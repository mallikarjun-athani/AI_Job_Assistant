from pathlib import PurePosixPath

from django.conf import settings
from django.db import models

from .validators import validate_resume_file


def resume_upload_to(instance, filename):
	return f'resumes/user_{instance.user_id}/{filename}'


class Resume(models.Model):
	class FileType(models.TextChoices):
		PDF = 'PDF', 'PDF'
		DOCX = 'DOCX', 'DOCX'

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resumes')
	file = models.FileField(upload_to=resume_upload_to, validators=[validate_resume_file])
	original_filename = models.CharField(max_length=255)
	file_type = models.CharField(max_length=4, choices=FileType.choices)
	file_size = models.PositiveBigIntegerField()
	extracted_text = models.TextField()
	uploaded_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-uploaded_at']

	def __str__(self):
		return self.original_filename

	@property
	def file_size_display(self):
		if self.file_size < 1024 * 1024:
			return f'{self.file_size / 1024:.0f} KB'
		return f'{self.file_size / (1024 * 1024):.1f} MB'

	@staticmethod
	def clean_original_filename(filename):
		return PurePosixPath(str(filename).replace('\\', '/')).name[:255]
