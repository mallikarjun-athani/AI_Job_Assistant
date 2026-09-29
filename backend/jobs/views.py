import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Job
from .providers import AdzunaJobProvider
from .services import JobDiscoveryError, discover_jobs_for_user

logger = logging.getLogger(__name__)


@login_required
def job_list(request):
    jobs = Job.objects.all()
    filters = {
        'location': request.GET.get('location', '').strip(),
        'employment_type': request.GET.get('employment_type', '').strip(),
        'experience_level': request.GET.get('experience_level', '').strip(),
        'source': request.GET.get('source', '').strip(),
    }

    if filters['location']:
        jobs = jobs.filter(location__icontains=filters['location'])
    if filters['employment_type']:
        jobs = jobs.filter(employment_type__icontains=filters['employment_type'])
    if filters['experience_level']:
        jobs = jobs.filter(experience_level__icontains=filters['experience_level'])
    if filters['source']:
        jobs = jobs.filter(source__icontains=filters['source'])

    paginator = Paginator(jobs.order_by('created_at'), 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(
        request,
        'jobs/job_list.html',
        {
            'jobs': page_obj.object_list,
            'page_obj': page_obj,
            'total_jobs': jobs.count(),
            'filters': filters,
            'discovery_summary': request.GET.get('summary'),
        },
    )


@login_required
@require_POST
def discover_jobs(request):
    try:
        saved_count, jobs, queries, location = discover_jobs_for_user(request.user, provider=AdzunaJobProvider())
    except JobDiscoveryError as error:
        messages.error(request, str(error))
        return render(
            request,
            'jobs/job_list.html',
            {
                'jobs': [],
                'page_obj': None,
                'total_jobs': 0,
                'discovery_summary': str(error),
                'queries': [],
                'location': '',
            },
        )
    except Exception:
        logger.exception('Unable to discover jobs for user %s.', request.user.pk)
        messages.error(request, 'Job search is temporarily unavailable. Please try again later.')
        return render(
            request,
            'jobs/job_list.html',
            {
                'jobs': [],
                'page_obj': None,
                'total_jobs': 0,
                'discovery_summary': 'Job search is temporarily unavailable. Please try again later.',
                'queries': [],
                'location': '',
            },
        )


    messages.success(request, f'{saved_count} jobs found')
    return render(
        request,
        'jobs/job_list.html',
        {
            'jobs': list(jobs),
            'page_obj': None,
            'total_jobs': saved_count,
            'discovery_summary': f'{saved_count} jobs found',
            'queries': queries,
            'location': location,
        },
    )


@login_required
def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)
    safe_url = job.job_url if job.job_url.startswith(('http://', 'https://')) else ''
    return render(request, 'jobs/job_detail.html', {'job': job, 'safe_url': safe_url})
