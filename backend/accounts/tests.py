from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Profile, User, validate_profile_picture_size


class AccountFlowTests(TestCase):
    password = 'Strong-Test-Pass-942!'

    def setUp(self):
        self.client.defaults['HTTP_HOST'] = 'localhost'

    def create_user(self, email='person@example.com', **extra_fields):
        return User.objects.create_user(email=email, password=self.password, **extra_fields)

    def test_registration_creates_profile_and_logs_user_in(self):
        response = self.client.post(
            reverse('register'),
            {
                'first_name': 'Taylor',
                'last_name': 'Reed',
                'email': 'Taylor@example.com',
                'password1': self.password,
                'password2': self.password,
            },
        )

        self.assertRedirects(response, reverse('dashboard'))
        user = User.objects.get(email='taylor@example.com')
        self.assertTrue(user.check_password(self.password))
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_registration_rejects_duplicate_email_case_insensitively(self):
        self.create_user(email='person@example.com')

        response = self.client.post(
            reverse('register'),
            {
                'first_name': 'Another',
                'last_name': 'Person',
                'email': 'PERSON@example.com',
                'password1': self.password,
                'password2': self.password,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'An account with this email already exists.')
        self.assertEqual(User.objects.count(), 1)

    def test_login_with_valid_credentials(self):
        self.create_user()

        response = self.client.post(
            reverse('login'),
            {'username': 'PERSON@example.com', 'password': self.password},
        )

        self.assertRedirects(response, reverse('dashboard'))

    def test_login_with_invalid_credentials_shows_generic_message(self):
        self.create_user()

        response = self.client.post(
            reverse('login'),
            {'username': 'person@example.com', 'password': 'incorrect-password'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a correct email and password.')

    def test_dashboard_requires_authentication(self):
        response = self.client.get(reverse('dashboard'))

        self.assertRedirects(
            response,
            f'{reverse("login")}?next={reverse("dashboard")}',
        )

    def test_authenticated_dashboard_shows_account_summary(self):
        user = self.create_user(first_name='Taylor')
        Profile.objects.create(user=user, location='Seattle')
        self.client.force_login(user)

        response = self.client.get(reverse('dashboard'))

        self.assertContains(response, 'Welcome, Taylor')
        self.assertContains(response, 'person@example.com')
        self.assertContains(response, 'Resume Analysis')

    def test_profile_update_changes_only_profile_fields(self):
        user = self.create_user(first_name='Taylor', last_name='Reed')
        Profile.objects.create(user=user)
        self.client.force_login(user)

        response = self.client.post(
            reverse('profile'),
            {
                'first_name': 'Jordan',
                'last_name': 'Reed',
                'email': 'jordan@example.com',
                'phone': '555-0100',
                'location': 'Seattle',
                'bio': 'Software developer',
                'github_url': 'https://github.com/jordan',
                'linkedin_url': 'https://www.linkedin.com/in/jordan',
                'portfolio_url': 'https://jordan.example.com',
            },
        )

        self.assertRedirects(response, reverse('profile'))
        user.refresh_from_db()
        user.profile.refresh_from_db()
        self.assertEqual(user.first_name, 'Jordan')
        self.assertEqual(user.email, 'jordan@example.com')
        self.assertEqual(user.profile.phone, '555-0100')
        self.assertEqual(user.profile.location, 'Seattle')
        self.assertTrue(user.check_password(self.password))

    def test_logout_ends_session_and_redirects_to_login(self):
        user = self.create_user()
        self.client.force_login(user)

        response = self.client.post(reverse('logout'))

        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_password_change_uses_django_password_form(self):
        user = self.create_user()
        self.client.force_login(user)
        new_password = 'New-Strong-Pass-195!'

        response = self.client.post(
            reverse('change_password'),
            {
                'old_password': self.password,
                'new_password1': new_password,
                'new_password2': new_password,
            },
            follow=True,
        )

        self.assertRedirects(response, reverse('change_password'))
        user.refresh_from_db()
        self.assertTrue(user.check_password(new_password))
        self.assertContains(response, 'Your password has been changed.')

    def test_profile_completion_percentage(self):
        user = self.create_user(first_name='Taylor', last_name='Reed')
        profile = Profile.objects.create(user=user)

        self.assertEqual(profile.completion_percentage, 30)

    def test_profile_picture_size_limit(self):
        upload = SimpleUploadedFile('large.png', b'x' * (5 * 1024 * 1024 + 1))

        with self.assertRaises(ValidationError):
            validate_profile_picture_size(upload)
