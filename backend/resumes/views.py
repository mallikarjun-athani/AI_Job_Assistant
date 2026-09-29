import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import SuspiciousFileOperation
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ai_assistant.services import (
	AIAnalysisTimedOut,
	AIRateLimited,
	AIServiceNotConfigured,
	GroqResumeAnalyzer,
	GroqServiceUnavailable,
	InvalidAIResponse,
	ResumeAnalysisError,
	ResumeTextTooLarge,
)

from .forms import ResumeUploadForm
from .models import Resume, ResumeAnalysis
from .services import ResumeExtractionError, extract_resume_text


logger = logging.getLogger(__name__)


@login_required
def resume_list(request):
	resumes = Resume.objects.filter(user=request.user).select_related('analysis')
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
@require_POST
def resume_analyze(request, pk):
	resume = get_object_or_404(Resume, pk=pk, user=request.user)
	if not resume.extracted_text or not resume.extracted_text.strip():
		messages.error(request, 'This resume does not contain enough text to analyze.')
		return redirect('resumes:resume_detail', pk=resume.pk)

	logger.info('Resume analysis started for resume_id=%s user_id=%s.', resume.pk, request.user.pk)
	try:
		analysis_data = GroqResumeAnalyzer().analyze_resume(resume.extracted_text)
	except AIServiceNotConfigured:
		message = 'AI service is not configured. Please contact the administrator.'
	except ResumeTextTooLarge:
		message = 'This resume is too large to analyze in one request.'
	except AIAnalysisTimedOut:
		message = 'AI analysis timed out. Please try again.'
	except AIRateLimited:
		message = 'AI service is temporarily busy. Please try again later.'
	except InvalidAIResponse:
		message = 'AI returned an invalid response. Please try again.'
	except (GroqServiceUnavailable, ResumeAnalysisError):
		message = 'Unable to analyze the resume right now. Please try again.'
	else:
		with transaction.atomic():
			analysis, _ = ResumeAnalysis.objects.update_or_create(
				resume=resume,
				defaults=analysis_data,
			)
		logger.info('Resume analysis completed for resume_id=%s user_id=%s.', resume.pk, request.user.pk)
		messages.success(request, 'Resume analysis is ready.')
		return redirect('resumes:resume_analysis', pk=resume.pk)

	logger.warning('Resume analysis failed for resume_id=%s user_id=%s.', resume.pk, request.user.pk)
	messages.error(request, message)
	return redirect('resumes:resume_detail', pk=resume.pk)


@login_required
def resume_analysis(request, pk):
	analysis = get_object_or_404(
		ResumeAnalysis.objects.select_related('resume').filter(resume__user=request.user),
		resume_id=pk,
	)
	return render(request, 'resumes/resume_analysis.html', {'analysis': analysis, 'resume': analysis.resume})


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
