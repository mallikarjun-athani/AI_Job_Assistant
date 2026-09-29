from django.urls import path

from . import views


app_name = 'resumes'

urlpatterns = [
    path('', views.resume_list, name='resume_list'),
    path('<int:pk>/', views.resume_detail, name='resume_detail'),
    path('<int:pk>/analyze/', views.resume_analyze, name='resume_analyze'),
    path('<int:pk>/analysis/', views.resume_analysis, name='resume_analysis'),
    path('<int:pk>/download/', views.resume_download, name='resume_download'),
    path('<int:pk>/delete/', views.resume_delete, name='resume_delete'),
]