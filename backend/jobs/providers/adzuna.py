from urllib.parse import urlencode

import requests
from django.conf import settings

from .base import JobProvider


class AdzunaJobProvider(JobProvider):
    def search_jobs(self, query, location=None, page=1):
        if not query:
            return []

        base_url = getattr(settings, 'ADZUNA_BASE_URL', 'https://api.adzuna.com/v1/api').rstrip('/')
        country = getattr(settings, 'ADZUNA_COUNTRY', 'in')
        app_id = getattr(settings, 'ADZUNA_APP_ID', '')
        app_key = getattr(settings, 'ADZUNA_APP_KEY', '')
        timeout = getattr(settings, 'ADZUNA_REQUEST_TIMEOUT', 10)

        if not app_id or not app_key:
            raise ValueError('Adzuna API credentials are not configured.')

        cleaned_query = ' '.join(str(query).split())
        location_value = ' '.join(str(location or '').split()) or 'India'
        params = {
            'app_id': app_id,
            'app_key': app_key,
            'what': cleaned_query,
            'where': location_value,
            'results_per_page': getattr(settings, 'JOB_DISCOVERY_JOBS_PER_QUERY', 10),
        }
        request_page = 1
        request_url = f'{base_url}/jobs/{country}/search/{request_page}/?{urlencode(params)}'
        response = requests.get(request_url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        return [self.normalize_job(item) for item in payload.get('results', [])]

    def normalize_job(self, raw_data):
        if not isinstance(raw_data, dict):
            return {}

        location_data = raw_data.get('location') or {}
        if isinstance(location_data, dict):
            location_value = location_data.get('display_name') or 'Remote'
        else:
            location_value = str(location_data or 'Remote')

        company_data = raw_data.get('company') or {}
        company_name = company_data.get('display_name') if isinstance(company_data, dict) else ''

        category_data = raw_data.get('category') or {}
        category_label = category_data.get('label') if isinstance(category_data, dict) else ''

        contract_type = raw_data.get('contract_type') or raw_data.get('employment_type') or ''
        employment_type = self._map_employment_type(contract_type)
        experience_level = self._map_experience_level(raw_data.get('experience_level'))

        normalized = {
            'provider': 'adzuna',
            'external_id': str(raw_data.get('id') or raw_data.get('external_id') or ''),
            'title': raw_data.get('title') or 'Untitled Role',
            'company_name': company_name or 'Unknown Company',
            'location': location_value or 'Remote',
            'description': raw_data.get('description') or '',
            'job_url': raw_data.get('redirect_url') or raw_data.get('job_url') or '',
            'employment_type': employment_type,
            'experience_level': experience_level,
            'salary_min': raw_data.get('salary_min'),
            'salary_max': raw_data.get('salary_max'),
            'salary_currency': raw_data.get('salary_currency') or '',
            'category': category_label or '',
            'source': 'Adzuna',
            'posted_at': raw_data.get('created') or raw_data.get('posted_at') or '',
            'raw_data': raw_data,
        }
        return normalized

    def _map_employment_type(self, value):
        mapping = {
            'full_time': 'Full-time',
            'part_time': 'Part-time',
            'contract': 'Contract',
            'permanent': 'Permanent',
            'temporary': 'Temporary',
            'internship': 'Internship',
        }
        if not value:
            return 'Full-time'
        return mapping.get(str(value).lower(), str(value).replace('_', ' ').title())

    def _map_experience_level(self, value):
        mapping = {
            'junior': 'Junior',
            'mid_level': 'Mid-Level',
            'mid-level': 'Mid-Level',
            'senior': 'Senior',
            'entry_level': 'Entry-Level',
            'entry-level': 'Entry-Level',
            'associate': 'Associate',
        }
        if not value:
            return ''
        return mapping.get(str(value).lower(), str(value).replace('_', ' ').title())
