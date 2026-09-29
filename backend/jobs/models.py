from django.db import models


class Job(models.Model):
    provider = models.CharField(max_length=50, default='adzuna')
    external_id = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    job_url = models.URLField(max_length=500)
    employment_type = models.CharField(max_length=80, blank=True)
    experience_level = models.CharField(max_length=80, blank=True)
    salary_min = models.BigIntegerField(null=True, blank=True)
    salary_max = models.BigIntegerField(null=True, blank=True)
    salary_currency = models.CharField(max_length=20, blank=True)
    category = models.CharField(max_length=120, blank=True)
    source = models.CharField(max_length=80, default='Adzuna')
    posted_at = models.DateTimeField(null=True, blank=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    raw_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(fields=['provider', 'external_id'], name='jobs_unique_provider_external_id'),
        ]

    def __str__(self):
        return f'{self.title} @ {self.company_name or self.provider}'
