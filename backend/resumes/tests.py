from io import BytesIO
from tempfile import TemporaryDirectory

import pymupdf
from docx import Document
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import User

from .models import Resume
from .services import extract_docx_text, extract_pdf_text
from .views import resume_download


class ResumeFlowTests(TestCase):
	password = 'Strong-Test-Pass-942!'

	def setUp(self):
		media_directory = TemporaryDirectory()
		self.addCleanup(media_directory.cleanup)
		media_settings = override_settings(MEDIA_ROOT=media_directory.name)
		media_settings.enable()
		self.addCleanup(media_settings.disable)
		self.user = self.create_user()
		self.client.force_login(self.user)

	def create_user(self, email='candidate@example.com'):
		return User.objects.create_user(email=email, password=self.password)

	def create_pdf(self, text='Jordan Candidate'):
		document = pymupdf.open()
		page = document.new_page()
		page.insert_text((72, 72), text)
		contents = document.tobytes()
		document.close()
		return SimpleUploadedFile('candidate.pdf', contents, content_type='application/pdf')

	def create_docx(self, paragraphs=None, filename='candidate.docx'):
		document = Document()
		for paragraph in paragraphs or ['Jordan Candidate', 'Skills: Python, Django']:
			document.add_paragraph(paragraph)
		contents = BytesIO()
		document.save(contents)
		return SimpleUploadedFile(
			filename,
			contents.getvalue(),
			content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
		)

	def upload_url(self):
		return reverse('resumes:resume_list')

	def test_authenticated_user_can_upload_pdf(self):
		response = self.client.post(self.upload_url(), {'file': self.create_pdf()})

		self.assertRedirects(response, self.upload_url())
		resume = Resume.objects.get(user=self.user)
		self.assertEqual(resume.file_type, Resume.FileType.PDF)
		self.assertIn('Jordan Candidate', resume.extracted_text)
		self.assertTrue(resume.file.storage.exists(resume.file.name))
		self.assertTrue(resume.file.name.startswith(f'resumes/user_{self.user.pk}/'))

	def test_authenticated_user_can_upload_docx(self):
		response = self.client.post(self.upload_url(), {'file': self.create_docx()})

		self.assertRedirects(response, self.upload_url())
		resume = Resume.objects.get(user=self.user)
		self.assertEqual(resume.file_type, Resume.FileType.DOCX)
		self.assertIn('Skills: Python, Django', resume.extracted_text)

	def test_unauthenticated_user_cannot_upload(self):
		self.client.logout()

		response = self.client.post(self.upload_url(), {'file': self.create_pdf()})

		self.assertRedirects(response, f'{reverse("login")}?next={self.upload_url()}')
		self.assertEqual(Resume.objects.count(), 0)

	def test_invalid_file_extension_is_rejected(self):
		upload = SimpleUploadedFile('program.exe', b'MZ executable')

		response = self.client.post(self.upload_url(), {'file': upload})

		self.assertContains(response, 'Only PDF and DOCX resume files are supported.')
		self.assertEqual(Resume.objects.count(), 0)

	def test_file_larger_than_five_mb_is_rejected(self):
		upload = SimpleUploadedFile('large.pdf', b'x' * (5 * 1024 * 1024 + 1))

		response = self.client.post(self.upload_url(), {'file': upload})

		self.assertContains(response, 'File size must be 5 MB or smaller.')
		self.assertEqual(Resume.objects.count(), 0)

	def test_file_contents_must_match_supported_document_type(self):
		upload = SimpleUploadedFile('not-a-pdf.pdf', b'<html>not a PDF</html>')

		response = self.client.post(self.upload_url(), {'file': upload})

		self.assertContains(response, 'The file content is not a valid PDF or DOCX document.')
		self.assertEqual(Resume.objects.count(), 0)

	def test_pdf_text_extraction_reads_all_pages_in_order(self):
		document = pymupdf.open()
		for text in ('First page text', 'Second page text'):
			page = document.new_page()
			page.insert_text((72, 72), text)
		upload = SimpleUploadedFile('multi.pdf', document.tobytes())
		document.close()

		extracted = extract_pdf_text(upload)

		self.assertLess(extracted.index('First page text'), extracted.index('Second page text'))

	def test_docx_text_extraction_preserves_paragraphs(self):
		upload = self.create_docx(['Name', 'Skills:', 'Python', 'Django'])

		extracted = extract_docx_text(upload)

		self.assertEqual(extracted, 'Name\nSkills:\nPython\nDjango')

	def test_corrupted_and_empty_documents_are_rejected_without_records(self):
		for upload in (
			SimpleUploadedFile('corrupt.pdf', b'%PDF-not-a-real-document'),
			self.create_docx(['']),
		):
			with self.subTest(filename=upload.name):
				response = self.client.post(self.upload_url(), {'file': upload})
				self.assertEqual(response.status_code, 200)
		self.assertEqual(Resume.objects.count(), 0)

	def test_resume_list_shows_only_current_users_resumes(self):
		own_resume = self.create_owned_resume()
		other_user = self.create_user('another@example.com')
		other_resume = self.create_owned_resume(user=other_user, filename='private.pdf')

		response = self.client.get(self.upload_url())

		self.assertContains(response, own_resume.original_filename)
		self.assertNotContains(response, other_resume.original_filename)

	def test_user_can_view_own_resume_and_extracted_text_is_escaped(self):
		resume = self.create_owned_resume(extracted_text='<script>alert(1)</script>')

		response = self.client.get(reverse('resumes:resume_detail', args=[resume.pk]))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
		self.assertNotContains(response, '<script>alert(1)</script>')

	def test_user_cannot_view_another_users_resume(self):
		other_resume = self.create_owned_resume(user=self.create_user('another@example.com'))

		response = self.client.get(reverse('resumes:resume_detail', args=[other_resume.pk]))

		self.assertEqual(response.status_code, 404)

	def test_user_can_delete_own_resume_and_stored_file(self):
		resume = self.create_owned_resume()
		stored_name = resume.file.name

		response = self.client.post(reverse('resumes:resume_delete', args=[resume.pk]))

		self.assertRedirects(response, self.upload_url())
		self.assertFalse(Resume.objects.filter(pk=resume.pk).exists())
		self.assertFalse(resume.file.storage.exists(stored_name))

	def test_delete_confirmation_does_not_delete_on_get(self):
		resume = self.create_owned_resume()

		response = self.client.get(reverse('resumes:resume_delete', args=[resume.pk]))

		self.assertContains(response, 'Are you sure you want to delete this resume?')
		self.assertTrue(Resume.objects.filter(pk=resume.pk).exists())

	def test_user_cannot_delete_another_users_resume(self):
		other_resume = self.create_owned_resume(user=self.create_user('another@example.com'))

		response = self.client.post(reverse('resumes:resume_delete', args=[other_resume.pk]))

		self.assertEqual(response.status_code, 404)
		self.assertTrue(Resume.objects.filter(pk=other_resume.pk).exists())

	def test_delete_requires_csrf_token(self):
		resume = self.create_owned_resume()
		csrf_client = Client(enforce_csrf_checks=True)
		csrf_client.force_login(self.user)

		response = csrf_client.post(reverse('resumes:resume_delete', args=[resume.pk]))

		self.assertEqual(response.status_code, 403)
		self.assertTrue(Resume.objects.filter(pk=resume.pk).exists())

	def test_user_can_download_own_resume(self):
		resume = self.create_owned_resume()
		request = RequestFactory().get(reverse('resumes:resume_download', args=[resume.pk]))
		request.user = self.user

		response = resume_download(request, resume.pk)

		self.assertEqual(response.status_code, 200)
		self.assertIn('attachment', response['Content-Disposition'])
		self.assertIn(resume.original_filename, response['Content-Disposition'])
		response.file_to_stream.close()

	def test_user_cannot_download_another_users_resume(self):
		other_resume = self.create_owned_resume(user=self.create_user('another@example.com'))

		response = self.client.get(reverse('resumes:resume_download', args=[other_resume.pk]))

		self.assertEqual(response.status_code, 404)

	def test_missing_resume_file_shows_a_friendly_message(self):
		resume = self.create_owned_resume()
		resume.file.storage.delete(resume.file.name)

		response = self.client.get(reverse('resumes:resume_download', args=[resume.pk]), follow=True)

		self.assertRedirects(response, reverse('resumes:resume_detail', args=[resume.pk]))
		self.assertContains(response, 'This resume file is currently unavailable.')

	def test_dashboard_displays_resume_count_and_manage_link(self):
		self.create_owned_resume()

		response = self.client.get(reverse('dashboard'))

		self.assertContains(response, 'Total Resumes: 1')
		self.assertContains(response, reverse('resumes:resume_list'))

	def create_owned_resume(self, user=None, filename='candidate.pdf', extracted_text='Resume text'):
		user = user or self.user
		return Resume.objects.create(
			user=user,
			file=SimpleUploadedFile(filename, b'%PDF-1.7 test file'),
			original_filename=filename,
			file_type='PDF',
			file_size=20,
			extracted_text=extracted_text,
		)

# Create your tests here.
