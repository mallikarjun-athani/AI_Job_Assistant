import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import SuspiciousFileOperation
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ResumeUploadForm
from .models import Resume
from .services import ResumeExtractionError, extract_resume_text


logger = logging.getLogger(__name__)


@login_required
def resume_list(request):
	resumes = Resume.objects.filter(user=request.user)
	form = ResumeUploadForm(request.POST or None, request.FILES or None)

	if request.method == 'POST' and form.is_valid():
		uploaded_file = form.cleaned_data['file']
		try:
			extracted_text = extract_resume_text(uploaded_file)
		except ResumeExtractionError as error:
			form.add_error('file', str(error))
		else:
			resume = form.save(commit=False)
			resume.user = request.user
			resume.original_filename = Resume.clean_original_filename(uploaded_file.name)
			resume.file_type = uploaded_file.name.rsplit('.', 1)[-1].upper()
			resume.file_size = uploaded_file.size
			resume.extracted_text = extracted_text
			try:
				resume.save()
			except (OSError, SuspiciousFileOperation):
				logger.exception('Unable to store an uploaded resume for user %s.', request.user.pk)
				form.add_error(None, 'The resume could not be stored. Please try again.')
			else:
				messages.success(request, 'Your resume has been uploaded.')
				return redirect('resumes:resume_list')

	return render(request, 'resumes/resume_list.html', {'form': form, 'resumes': resumes})


@login_required
def resume_detail(request, pk):
	resume = get_object_or_404(Resume, pk=pk, user=request.user)
	try:
		file_available = bool(resume.file) and resume.file.storage.exists(resume.file.name)
	except Exception:
		logger.exception('Unable to check stored resume %s.', resume.pk)
		file_available = False
	return render(
		request,
		'resumes/resume_detail.html',
		{'resume': resume, 'file_available': file_available},
	)


@login_required
def resume_download(request, pk):
	resume = get_object_or_404(Resume, pk=pk, user=request.user)
	try:
		file_handle = resume.file.open('rb')
	except FileNotFoundError:
		messages.error(request, 'This resume file is currently unavailable.')
		return redirect('resumes:resume_detail', pk=resume.pk)
	except Exception:
		logger.exception('Unable to open stored resume %s for download.', resume.pk)
		messages.error(request, 'This resume file is currently unavailable.')
		return redirect('resumes:resume_detail', pk=resume.pk)
	return FileResponse(file_handle, as_attachment=True, filename=resume.original_filename)


@login_required
def resume_delete(request, pk):
	resume = get_object_or_404(Resume, pk=pk, user=request.user)
	if request.method == 'POST':
		try:
			resume.file.storage.delete(resume.file.name)
		except Exception:
			logger.exception('Unable to delete stored resume file %s.', resume.pk)
			messages.error(request, 'The resume file could not be deleted. Please try again.')
			return redirect('resumes:resume_detail', pk=resume.pk)
		resume.delete()
		messages.success(request, 'Your resume has been deleted.')
		return redirect('resumes:resume_list')
	return render(request, 'resumes/resume_confirm_delete.html', {'resume': resume})

# Create your views here.
