from django.contrib import admin

from .models import Resume


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
	list_display = ('user', 'original_filename', 'file_type', 'file_size', 'uploaded_at', 'updated_at')
	list_filter = ('file_type', 'uploaded_at')
	search_fields = ('user__email', 'original_filename')
	readonly_fields = ('uploaded_at', 'updated_at')
