from datetime import datetime, timezone

from django.conf import settings
from django.db import transaction
from django.utils import timezone as django_timezone

from .models import Job


class JobDiscoveryError(ValueError):
    pass


def _coerce_datetime(value):
    if value in (None, ''):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).replace('Z', '+00:00')
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        return django_timezone.make_aware(dt, timezone.utc)
    return dt.astimezone(timezone.utc)


def get_latest_resume_for_user(user):
    return user.resumes.order_by('-uploaded_at').select_related('analysis').first()


def get_latest_analyzed_resume_for_user(user):
    return (
        user.resumes.filter(analysis__isnull=False)
        .select_related('analysis')
        .order_by('-analysis__updated_at', '-uploaded_at')
        .first()
    )


def generate_search_queries(analysis_data, limit=None):
    max_queries = limit or getattr(settings, 'JOB_DISCOVERY_MAX_QUERIES', 5)
    candidates = []

    analysis = analysis_data if isinstance(analysis_data, dict) else {}

    def add_candidate(value):
        if value is None:
            return
        if isinstance(value, str):
            cleaned = ' '.join(value.split())
            if cleaned:
                candidates.append(cleaned)
            return
        if isinstance(value, dict):
            for key in ('job_title', 'title', 'role', 'name', 'position'):
                if key in value:
                    add_candidate(value.get(key))
            for key in ('skills', 'technologies'):
                if key in value:
                    add_candidate(value.get(key))
            return
        if isinstance(value, list):
            for item in value:
                add_candidate(item)

    for field in ('target_roles', 'experience'):
        add_candidate(analysis.get(field))

    for field in ('skills', 'keywords'):
        add_candidate(analysis.get(field))

    unique_queries = []
    seen = set()
    for candidate in candidates:
        key = candidate.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique_queries.append(candidate)
        if len(unique_queries) >= max_queries:
            break

    return unique_queries[:max_queries]


def discover_jobs_for_resume(resume, discovered_jobs, provider='adzuna'):
    if not discovered_jobs:
        return 0

    unique_jobs = []
    seen = set()
    for job_data in discovered_jobs:
        if not isinstance(job_data, dict):
            continue
        external_id = str(job_data.get('external_id') or job_data.get('id') or '').strip()
        if not external_id:
            continue
        key = (str(job_data.get('provider', provider)).strip() or provider, external_id)
        if key in seen:
            continue
        seen.add(key)
        unique_jobs.append(job_data)

    with transaction.atomic():
        saved_count = 0
        for job_data in unique_jobs:
            normalized = dict(job_data)
            normalized.setdefault('provider', provider)
            normalized.setdefault('source', 'Adzuna')
            external_id = str(normalized.get('external_id') or normalized.get('id') or '').strip()
            if not external_id:
                continue
            location = normalized.get('location') or 'Remote'
            title = normalized.get('title') or 'Untitled Role'
            company_name = normalized.get('company_name') or 'Unknown Company'
            defaults = {
                'title': title,
                'company_name': company_name,
                'location': str(location),
                'description': normalized.get('description') or '',
                'job_url': normalized.get('job_url') or '',
                'employment_type': normalized.get('employment_type') or '',
                'experience_level': normalized.get('experience_level') or '',
                'salary_min': normalized.get('salary_min'),
                'salary_max': normalized.get('salary_max'),
                'salary_currency': normalized.get('salary_currency') or '',
                'category': normalized.get('category') or '',
                'source': normalized.get('source') or 'Adzuna',
                'posted_at': _coerce_datetime(normalized.get('posted_at')),
                'raw_data': normalized.get('raw_data') or normalized,
            }
            job, created = Job.objects.update_or_create(
                provider=str(normalized.get('provider', provider)),
                external_id=external_id,
                defaults=defaults,
            )
            if created or job.last_seen_at is None:
                saved_count += 1
            else:
                saved_count += 1
    return saved_count


def discover_jobs_for_user(user, provider=None):
    if provider is None:
        from .providers import AdzunaJobProvider
        provider = AdzunaJobProvider()

    latest_resume = get_latest_resume_for_user(user)
    if latest_resume is None:
        raise JobDiscoveryError('Please upload a resume first.')

    resume = get_latest_analyzed_resume_for_user(user)
    if resume is None:
        raise JobDiscoveryError('Please analyze your resume before discovering jobs.')

    analysis = resume.analysis
    analysis_data = {
        'target_roles': list(analysis.target_roles or []),
        'skills': list(analysis.skills or []),
        'keywords': list(analysis.keywords or []),
    }
    queries = generate_search_queries(analysis_data)
    if not queries:
        raise JobDiscoveryError('No job search queries could be created from your resume.')

    profile = getattr(user, 'profile', None)
    profile_location = getattr(profile, 'location', '') if profile else ''
    location = ' '.join(str(profile_location or '').split()) or 'India'

    collected_jobs = []
    for query in queries:
        result = provider.search_jobs(query, location=location, page=1)
        collected_jobs.extend(result)

    saved_count = discover_jobs_for_resume(resume, collected_jobs, provider='adzuna')
    if saved_count == 0:
        raise JobDiscoveryError(
            f'No jobs were found for your resume profile using the location "{location}". '
            'Try simplifying your profile location (e.g. use "Bengaluru" instead of a full address) and try again.'
        )
    jobs = Job.objects.order_by('-last_seen_at')[:20]
    return saved_count, jobs, queries, location
