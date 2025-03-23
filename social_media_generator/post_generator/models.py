# post_generator/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os
import uuid

class Platform(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=100, help_text="Font Awesome icon class")
    max_text_length = models.PositiveIntegerField(default=280)
    image_aspect_ratio = models.CharField(max_length=20, default="1:1", help_text="Format: width:height")
    
    def __str__(self):
        return self.name

def post_image_path(instance, filename):
    # Generate a unique filename with the original extension
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('generated_posts', filename)

class PostTemplate(models.Model):
    CATEGORY_CHOICES = [
        ('promotional', 'Promotional'),
        ('informational', 'Informational'),
        ('engagement', 'Engagement'),
        ('announcement', 'Announcement'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    template_text = models.TextField(help_text="Use {variables} for dynamic content")
    variables = models.JSONField(default=dict, help_text="JSON object with variable names as keys and descriptions as values")
    background_color = models.CharField(max_length=20, default="#FFFFFF")
    text_color = models.CharField(max_length=20, default="#000000")
    is_public = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class GeneratedPost(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('published', 'Published'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    template = models.ForeignKey(PostTemplate, on_delete=models.CASCADE)
    content = models.TextField()
    variables_used = models.JSONField(default=dict)
    image = models.ImageField(upload_to=post_image_path, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    schedule_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Post for {self.platform.name} by {self.user.username}"
    
    def is_scheduled(self):
        return self.status == 'scheduled' and self.schedule_time and self.schedule_time > timezone.now()

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    preferred_platforms = models.ManyToManyField(Platform, blank=True)
    default_hashtags = models.TextField(blank=True, help_text="Enter hashtags separated by spaces")
    
    def __str__(self):
        return f"Profile of {self.user.username}"