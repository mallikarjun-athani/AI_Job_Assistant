from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
	list_display = (
		'user',
		'phone',
		'location',
		'github_url',
		'linkedin_url',
		'portfolio_url',
		'created_at',
		'updated_at',
	)
	search_fields = ('user__email', 'phone', 'location')
	readonly_fields = ('created_at', 'updated_at')
