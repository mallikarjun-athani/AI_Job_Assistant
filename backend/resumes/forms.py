from django import forms

from .models import Resume


class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ['file']
        labels = {'file': 'Choose Resume'}
        widgets = {'file': forms.ClearableFileInput(attrs={'accept': '.pdf,.docx'})}