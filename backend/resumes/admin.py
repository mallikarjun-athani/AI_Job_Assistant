from django.contrib import admin

from .models import Resume, ResumeAnalysis


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
	list_display = ('user', 'original_filename', 'file_type', 'file_size', 'uploaded_at', 'updated_at')
	list_filter = ('file_type', 'uploaded_at')
	search_fields = ('user__email', 'original_filename')
	readonly_fields = ('uploaded_at', 'updated_at')


@admin.register(ResumeAnalysis)
class ResumeAnalysisAdmin(admin.ModelAdmin):
	list_display = ('resume', 'created_at', 'updated_at')
	search_fields = ('resume__original_filename', 'resume__user__email')
	readonly_fields = ('created_at', 'updated_at')
