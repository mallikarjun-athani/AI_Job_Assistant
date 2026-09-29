from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Profile, User
from resumes.models import Resume, ResumeAnalysis

from .models import Job
from .services import discover_jobs_for_resume, generate_search_queries


@override_settings(
    ADZUNA_APP_ID='test-app-id',
    ADZUNA_APP_KEY='test-app-key',
    ADZUNA_COUNTRY='in',
    ADZUNA_BASE_URL='https://api.adzuna.com/v1/api',
)
class JobDiscoveryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='candidate@example.com', password='Strong-Test-Pass-942!')
        self.profile = Profile.objects.create(user=self.user, location='Bangalore')
        self.resume = Resume.objects.create(
            user=self.user,
            file='resumes/test.pdf',
            original_filename='resume.pdf',
            file_type='PDF',
            file_size=2048,
            extracted_text='Python Django developer with experience in PostgreSQL and backend services.',
        )
        self.analysis = ResumeAnalysis.objects.create(
            resume=self.resume,
            skills=['Python', 'Django', 'PostgreSQL', 'REST API'],
            keywords=['backend', 'aws', 'api'],
            personal_info={'name': 'Test User'},
            target_roles=['Python Developer', 'Django Developer', 'Backend Developer'],
        )

    def test_authenticated_user_can_discover_jobs(self):
        mock_provider = Mock()
        mock_provider.search_jobs.return_value = [
            {
                'provider': 'adzuna',
                'external_id': 'job-1',
                'title': 'Python Developer',
                'company_name': 'Test Technologies',
                'location': 'Bangalore',
                'description': 'Build Python backend services',
                'job_url': 'https://example.com/jobs/1',
                'employment_type': 'Full-time',
                'experience_level': 'Mid-Level',
                'salary_min': 600000,
                'salary_max': 900000,
                'salary_currency': 'INR',
                'posted_at': '2026-09-20T00:00:00Z',
                'source': 'Adzuna',
            },
            {
                'provider': 'adzuna',
                'external_id': 'job-2',
                'title': 'Django Developer',
                'company_name': 'Second Tech',
                'location': 'Bangalore',
                'description': 'Django and Python development',
                'job_url': 'https://example.com/jobs/2',
                'employment_type': 'Contract',
                'experience_level': 'Junior',
                'salary_min': 500000,
                'salary_max': 700000,
                'salary_currency': 'INR',
                'posted_at': '2026-09-21T00:00:00Z',
                'source': 'Adzuna',
            },
        ]

        with patch('jobs.views.AdzunaJobProvider') as provider_class:
            provider_class.return_value = mock_provider
            self.client.force_login(self.user)
            response = self.client.post(reverse('jobs:discover'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2 jobs found')
        self.assertEqual(Job.objects.filter(provider='adzuna').count(), 2)

    def test_unauthenticated_user_cannot_discover_jobs(self):
        response = self.client.post(reverse('jobs:discover'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_user_without_resume_receives_correct_message(self):
        other_user = User.objects.create_user(email='noresume@example.com', password='Strong-Test-Pass-942!')
        self.client.force_login(other_user)

        response = self.client.post(reverse('jobs:discover'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please upload a resume first.')

    def test_user_without_analyzed_resume_receives_correct_message(self):
        self.resume.analysis.delete()
        self.client.force_login(self.user)

        response = self.client.post(reverse('jobs:discover'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please analyze your resume before discovering jobs.')

    @patch('jobs.providers.adzuna.requests.get')
    def test_adzuna_provider_is_called_with_expected_search_parameters(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'results': []}

        from jobs.providers.adzuna import AdzunaJobProvider

        provider = AdzunaJobProvider()
        provider.search_jobs('Python Developer', location='Bangalore', page=2)

        mock_get.assert_called_once()
        called_url = mock_get.call_args.args[0]
        self.assertIn('/search/1/', called_url)
        self.assertIn('Python+Developer', called_url)
        self.assertIn('where=Bangalore', called_url)
        self.assertIn('app_id=test-app-id', called_url)
        self.assertIn('app_key=test-app-key', called_url)

    def test_api_response_is_normalized_correctly(self):
        raw = {
            'id': 'job-123',
            'title': 'Python Developer',
            'company': {'display_name': 'Alpha Labs'},
            'location': {'display_name': 'Bangalore'},
            'description': 'Build Python apps',
            'redirect_url': 'https://example.com/jobs/123',
            'contract_type': 'full_time',
            'experience_level': 'mid_level',
            'salary_min': 400000,
            'salary_max': 600000,
            'salary_currency': 'INR',
            'created': '2026-09-18T10:00:00Z',
            'category': {'label': 'Engineering'},
        }

        from jobs.providers.adzuna import AdzunaJobProvider

        normalized = AdzunaJobProvider().normalize_job(raw)

        self.assertEqual(normalized['provider'], 'adzuna')
        self.assertEqual(normalized['external_id'], 'job-123')
        self.assertEqual(normalized['company_name'], 'Alpha Labs')
        self.assertEqual(normalized['location'], 'Bangalore')
        self.assertEqual(normalized['employment_type'], 'Full-time')
        self.assertEqual(normalized['experience_level'], 'Mid-Level')
        self.assertEqual(normalized['salary_currency'], 'INR')
        self.assertEqual(normalized['source'], 'Adzuna')

    def test_duplicate_jobs_are_not_created(self):
        job_data = {
            'provider': 'adzuna',
            'external_id': 'dup-1',
            'title': 'Python Developer',
            'company_name': 'Alpha Labs',
            'location': 'Bangalore',
            'description': 'Build Python apps',
            'job_url': 'https://example.com/jobs/dup-1',
            'employment_type': 'Full-time',
            'experience_level': 'Mid-Level',
            'source': 'Adzuna',
            'posted_at': '2026-09-18T10:00:00Z',
            'salary_min': 500000,
            'salary_max': 700000,
            'salary_currency': 'INR',
            'raw_data': {'id': 'dup-1'},
        }
        Job.objects.create(**job_data)

        saved = discover_jobs_for_resume(self.resume, [job_data], provider='adzuna')

        self.assertEqual(saved, 1)
        self.assertEqual(Job.objects.filter(provider='adzuna', external_id='dup-1').count(), 1)

    def test_multiple_search_queries_are_deduplicated(self):
        analysis = {'target_roles': ['Python Developer', 'python developer', 'Django Developer', 'Backend Developer', 'Python Developer']}

        queries = generate_search_queries(analysis)

        self.assertLessEqual(len(queries), 5)
        self.assertEqual(len(set(queries)), len(queries))
        self.assertIn('Python Developer', queries)

    def test_search_queries_use_experience_titles_when_target_roles_are_missing(self):
        analysis = {
            'target_roles': [],
            'skills': ['Python', 'Django'],
            'keywords': ['backend'],
            'experience': [
                {'job_title': 'Python Developer'},
                {'job_title': 'Backend Engineer'},
            ],
        }

        queries = generate_search_queries(analysis)

        self.assertIn('Python Developer', queries)
        self.assertIn('Backend Engineer', queries)

    @patch('jobs.providers.adzuna.requests.get')
    def test_api_timeout_is_handled(self, mock_get):
        from requests import Timeout

        mock_get.side_effect = Timeout('Timed out')

        with self.assertRaises(Exception):
            from jobs.providers.adzuna import AdzunaJobProvider

            AdzunaJobProvider().search_jobs('Python Developer', location='Bangalore')

    @patch('jobs.providers.adzuna.requests.get')
    def test_http_error_is_handled(self, mock_get):
        from requests import HTTPError

        mock_get.side_effect = HTTPError('403 Forbidden')

        with self.assertRaises(Exception):
            from jobs.providers.adzuna import AdzunaJobProvider

            AdzunaJobProvider().search_jobs('Python Developer', location='Bangalore')

    @patch('jobs.views.AdzunaJobProvider')
    def test_empty_results_are_handled(self, provider_class):
        provider_class.return_value.search_jobs.return_value = []
        self.client.force_login(self.user)

        response = self.client.post(reverse('jobs:discover'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No jobs were found for your current resume profile.')

    def test_job_detail_page_works(self):
        job = Job.objects.create(
            provider='adzuna',
            external_id='job-detail-1',
            title='Python Developer',
            company_name='Alpha Labs',
            location='Bangalore',
            description='Work with Python and Django',
            job_url='https://example.com/jobs/detail',
            employment_type='Full-time',
            experience_level='Mid-Level',
            source='Adzuna',
            posted_at='2026-09-18T10:00:00Z',
            raw_data={'id': 'job-detail-1'},
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('jobs:job_detail', args=[job.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Python Developer')
        self.assertContains(response, 'https://example.com/jobs/detail')

    def test_different_users_can_see_shared_discovered_jobs(self):
        other_user = User.objects.create_user(email='other@example.com', password='Strong-Test-Pass-942!')
        job = Job.objects.create(
            provider='adzuna',
            external_id='shared-job',
            title='Backend Engineer',
            company_name='Shared Inc',
            location='India',
            description='Experience in backend systems',
            job_url='https://example.com/jobs/shared',
            employment_type='Full-time',
            source='Adzuna',
            posted_at='2026-09-18T10:00:00Z',
            raw_data={'id': 'shared-job'},
        )

        for user in (self.user, other_user):
            self.client.force_login(user)
            response = self.client.get(reverse('jobs:job_list'))
            self.assertContains(response, 'Backend Engineer')

    def test_pagination_works(self):
        for index in range(15):
            Job.objects.create(
                provider='adzuna',
                external_id=f'page-{index}',
                title=f'Job {index}',
                company_name='Alpha Labs',
                location='Bangalore',
                description='Example description',
                job_url=f'https://example.com/jobs/page-{index}',
                employment_type='Full-time',
                source='Adzuna',
                posted_at='2026-09-18T10:00:00Z',
                raw_data={'id': f'page-{index}'},
            )
        self.client.force_login(self.user)

        response = self.client.get(reverse('jobs:job_list') + '?page=2')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Page 2')
        self.assertContains(response, 'Job 10')
