from django.contrib import admin

from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('provider', 'external_id', 'title', 'company_name', 'location', 'source', 'posted_at', 'first_seen_at', 'last_seen_at')
    list_filter = ('provider', 'source', 'location', 'employment_type')
    search_fields = ('title', 'company_name', 'external_id', 'location')
    readonly_fields = ('first_seen_at', 'last_seen_at', 'created_at', 'updated_at')
    fields = (
        'provider', 'external_id', 'title', 'company_name', 'location', 'employment_type', 'experience_level',
        'source', 'posted_at', 'salary_min', 'salary_max', 'salary_currency', 'category', 'job_url', 'description',
        'first_seen_at', 'last_seen_at', 'raw_data',
    )
