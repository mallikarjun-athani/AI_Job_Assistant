from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db.models.functions import Lower


def validate_profile_picture_size(image):
	max_size = 5 * 1024 * 1024
	if image.size > max_size:
		raise ValidationError('Profile pictures must be 5 MB or smaller.')


class UserManager(BaseUserManager):
	use_in_migrations = True

	def get_by_natural_key(self, username):
		return self.get(email__iexact=username)

	def create_user(self, email, password=None, **extra_fields):
		if not email:
			raise ValueError('An email address is required.')
		email = self.normalize_email(email).strip().lower()
		user = self.model(email=email, **extra_fields)
		if password:
			user.set_password(password)
		else:
			user.set_unusable_password()
		user.save(using=self._db)
		return user

	def create_superuser(self, email, password=None, **extra_fields):
		extra_fields.setdefault('is_staff', True)
		extra_fields.setdefault('is_superuser', True)
		extra_fields.setdefault('is_active', True)

		if extra_fields.get('is_staff') is not True:
			raise ValueError('A superuser must have is_staff=True.')
		if extra_fields.get('is_superuser') is not True:
			raise ValueError('A superuser must have is_superuser=True.')

		return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
	username = None
	email = models.EmailField(unique=True)

	USERNAME_FIELD = 'email'
	REQUIRED_FIELDS = []

	objects = UserManager()

	class Meta:
		constraints = [
			models.UniqueConstraint(Lower('email'), name='accounts_user_email_ci_unique'),
		]

	def __str__(self):
		return self.email


class Profile(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
	phone = models.CharField(max_length=30, blank=True)
	location = models.CharField(max_length=120, blank=True)
	bio = models.TextField(blank=True)
	github_url = models.URLField(max_length=200, blank=True)
	linkedin_url = models.URLField(max_length=200, blank=True)
	portfolio_url = models.URLField(max_length=200, blank=True)
	profile_picture = models.ImageField(
		upload_to='profile_pictures/',
		blank=True,
		validators=[
			FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
			validate_profile_picture_size,
		],
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	@property
	def completion_percentage(self):
		values = (
			self.user.first_name,
			self.user.last_name,
			self.user.email,
			self.phone,
			self.location,
			self.bio,
			self.github_url,
			self.linkedin_url,
			self.portfolio_url,
			bool(self.profile_picture),
		)
		completed = sum(bool(value.strip()) if isinstance(value, str) else value for value in values)
		return round(completed * 100 / len(values))

	def __str__(self):
		return f'{self.user.email} profile'
