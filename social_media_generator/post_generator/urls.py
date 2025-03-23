# post_generator/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Authentication and user profile
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    
    # Templates
    path('templates/', views.template_list, name='template_list'),
    path('templates/<int:pk>/', views.template_detail, name='template_detail'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<int:pk>/edit/', views.template_edit, name='template_edit'),
    
    # Posts
    path('posts/', views.post_list, name='post_list'),
    path('posts/create/', views.post_create, name='post_create'),
    path('posts/<int:pk>/', views.post_detail, name='post_detail'),
    path('posts/<int:pk>/delete/', views.post_delete, name='post_delete'),
    path('posts/<int:pk>/publish/', views.post_publish, name='post_publish'),
    
    # Ajax endpoints
    path('load-template-variables/', views.load_template_variables, name='load_template_variables'),
]