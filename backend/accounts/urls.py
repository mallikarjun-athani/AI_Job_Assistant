from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path(
        'change-password/',
        views.UserPasswordChangeView.as_view(),
        name='change_password',
    ),
]