from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import EmailAuthenticationForm, ProfileForm, RegistrationForm, UserProfileForm
from .models import Profile


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            user = form.save()
            Profile.objects.create(user=user)
        login(request, user)
        messages.success(request, 'Your account has been created.')
        return redirect('dashboard')

    return render(request, 'accounts/register.html', {'form': form})


class UserLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True
    template_name = 'accounts/login.html'


@login_required
def dashboard(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(
        request,
        'accounts/dashboard.html',
        {'profile': profile, 'resume_count': request.user.resumes.count()},
    )


@login_required
def profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    user_form = UserProfileForm(instance=request.user)
    profile_form = ProfileForm(instance=profile)

    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user_form.save()
                profile_form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')

    return render(
        request,
        'accounts/profile.html',
        {'user_form': user_form, 'profile_form': profile_form, 'profile': profile},
    )


class UserPasswordChangeView(SuccessMessageMixin, PasswordChangeView):
    template_name = 'accounts/change_password.html'
    success_url = reverse_lazy('change_password')
    success_message = 'Your password has been changed.'
