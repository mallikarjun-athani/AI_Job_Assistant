from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Profile, User


class RegistrationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = (
            'phone',
            'location',
            'bio',
            'github_url',
            'linkedin_url',
            'portfolio_url',
            'profile_picture',
        )
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 5}),
            'profile_picture': forms.ClearableFileInput(
                attrs={'accept': 'image/jpeg,image/png,image/webp'}
            ),
        }