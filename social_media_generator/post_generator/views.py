from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from .models import Platform, PostTemplate, GeneratedPost, UserProfile
from .forms import (
    CustomUserCreationForm, 
    UserProfileForm, 
    PostTemplateForm, 
    GeneratedPostForm, 
    DynamicPostGeneratorForm
)

import json
from PIL import Image, ImageDraw, ImageFont
import os
import io
from django.core.files.uploadedfile import InMemoryUploadedFile
from string import Formatter

def home(request):
    """Home page view with counters and recent templates"""
    template_count = PostTemplate.objects.filter(is_public=True).count()
    post_count = GeneratedPost.objects.count()
    user_count = UserProfile.objects.count()
    
    # Get featured templates
    featured_templates = PostTemplate.objects.filter(is_public=True).order_by('-created_at')[:6]
    
    platforms = Platform.objects.all()
    
    context = {
        'template_count': template_count,
        'post_count': post_count,
        'user_count': user_count,
        'featured_templates': featured_templates,
        'platforms': platforms,
    }
    
    return render(request, 'post_generator/home.html', context)

def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'post_generator/register.html', {'form': form})

@login_required
def dashboard(request):
    """User dashboard showing recent posts and templates"""
    # Get user's recent posts
    recent_posts = GeneratedPost.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Get user's templates and frequently used public templates
    user_templates = PostTemplate.objects.filter(created_by=request.user).order_by('-created_at')[:5]
    
    # Get frequently used templates from posts
    used_template_ids = GeneratedPost.objects.filter(user=request.user).values_list('template_id', flat=True)
    frequent_templates = PostTemplate.objects.filter(
        id__in=used_template_ids,
        is_public=True
    ).exclude(
        created_by=request.user
    ).distinct()[:5]
    
    # Upcoming scheduled posts
    scheduled_posts = GeneratedPost.objects.filter(
        user=request.user,
        status='scheduled',
        schedule_time__gt=timezone.now()
    ).order_by('schedule_time')[:5]
    
    context = {
        'recent_posts': recent_posts,
        'user_templates': user_templates,
        'frequent_templates': frequent_templates,
        'scheduled_posts': scheduled_posts,
    }
    
    return render(request, 'post_generator/dashboard.html', context)

@login_required
def profile(request):
    """User profile view and edit"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
    }
    
    return render(request, 'post_generator/profile.html', context)

@login_required
def template_list(request):
    """View all available templates"""
    # Get all public templates and user's private templates
    templates = PostTemplate.objects.filter(
        Q(is_public=True) | Q(created_by=request.user)
    ).order_by('-created_at')
    
    # Filter by category if provided
    category = request.GET.get('category')
    if category:
        templates = templates.filter(category=category)
    
    # Search by name if provided
    search = request.GET.get('search')
    if search:
        templates = templates.filter(name__icontains=search)
    
    # Pagination
    paginator = Paginator(templates, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': dict(PostTemplate.CATEGORY_CHOICES),
        'current_category': category,
        'search_term': search,
    }
    
    return render(request, 'post_generator/template_list.html', context)

@login_required
def template_detail(request, pk):
    """View a specific template"""
    template = get_object_or_404(PostTemplate, pk=pk)
    
    # Only allow access if the template is public or belongs to the user
    if not template.is_public and template.created_by != request.user:
        messages.error(request, "You don't have permission to view this template.")
        return redirect('template_list')
    
    # Get sample posts using this template
    sample_posts = GeneratedPost.objects.filter(
        template=template, 
        status='published'
    ).order_by('-created_at')[:3]
    
    context = {
        'template': template,
        'sample_posts': sample_posts,
    }
    
    return render(request, 'post_generator/template_detail.html', context)

@login_required
def template_create(request):
    """Create a new template"""
    if request.method == 'POST':
        form = PostTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            messages.success(request, 'Template created successfully!')
            return redirect('template_detail', pk=template.pk)
    else:
        form = PostTemplateForm()
    
    context = {
        'form': form,
        'title': 'Create Template',
    }
    
    return render(request, 'post_generator/template_form.html', context)

@login_required
def template_edit(request, pk):
    """Edit an existing template"""
    template = get_object_or_404(PostTemplate, pk=pk)
    
    # Only allow editing if the template belongs to the user
    if template.created_by != request.user:
        messages.error(request, "You don't have permission to edit this template.")
        return redirect('template_list')
    
    if request.method == 'POST':
        form = PostTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, 'Template updated successfully!')
            return redirect('template_detail', pk=template.pk)
    else:
        form = PostTemplateForm(instance=template)
    
    context = {
        'form': form,
        'title': 'Edit Template',
        'template': template,
    }
    
    return render(request, 'post_generator/template_form.html', context)

@login_required
def post_create(request):
    """Create a new post with dynamic form based on selected template"""
    initial_platform = None
    if hasattr(request.user, 'profile') and request.user.profile.preferred_platforms.exists():
        initial_platform = request.user.profile.preferred_platforms.first()
    
    form = DynamicPostGeneratorForm(user=request.user, initial={'platform': initial_platform})
    
    if request.method == 'POST':
        form = DynamicPostGeneratorForm(user=request.user, data=request.POST)
        if form.is_valid():
            platform_id = form.cleaned_data['platform'].id
            template_id = form.cleaned_data['template'].id
            
            # Get the template and extract variables
            template = get_object_or_404(PostTemplate, id=template_id)
            
            # Collect variables from form
            variables = {}
            for field_name, field_value in form.cleaned_data.items():
                if field_name.startswith('var_'):
                    var_name = field_name[4:]  # Remove 'var_' prefix
                    variables[var_name] = field_value
            
            # Generate post content by replacing placeholders
            content = template.template_text
            for var_name, var_value in variables.items():
                placeholder = '{' + var_name + '}'
                content = content.replace(placeholder, var_value)
            
            # Generate the image
            image_file = generate_post_image(template, variables, content)
            
            # Create the post
            post = GeneratedPost(
                user=request.user,
                platform_id=platform_id,
                template=template,
                content=content,
                variables_used=variables,
                status='draft'
            )
            
            if image_file:
                post.image = image_file
            
            post.save()
            
            messages.success(request, 'Post created successfully!')
            return redirect('post_detail', pk=post.pk)
        
        # If form is invalid but template_id is present, add dynamic fields
        elif 'template' in form.cleaned_data:
            template_id = form.cleaned_data['template'].id
            form.add_dynamic_fields(template_id)
    
    context = {
        'form': form,
    }
    
    return render(request, 'post_generator/post_create.html', context)

@login_required
@require_POST
def load_template_variables(request):
    """Ajax view to load template variables dynamically"""
    template_id = request.POST.get('template_id')
    
    try:
        template = PostTemplate.objects.get(id=template_id)
        form = DynamicPostGeneratorForm(user=request.user)
        form.add_dynamic_fields(template_id)
        
        # Render form fields as HTML
        form_html = render_to_string(
            'post_generator/partials/dynamic_fields.html',
            {'form': form, 'template': template}
        )
        
        return JsonResponse({
            'success': True,
            'form_html': form_html,
            'template_preview': {
                'background_color': template.background_color,
                'text_color': template.text_color,
                'template_text': template.template_text,
            }
        })
    
    except PostTemplate.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Template not found'})

@login_required
def post_list(request):
    """View all posts created by the user"""
    posts = GeneratedPost.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter by status if provided
    status = request.GET.get('status')
    if status:
        posts = posts.filter(status=status)
    
    # Filter by platform if provided
    platform = request.GET.get('platform')
    if platform:
        posts = posts.filter(platform_id=platform)
    
    # Pagination
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all platforms for filter dropdown
    platforms = Platform.objects.all()
    
    context = {
        'page_obj': page_obj,
        'platforms': platforms,
        'current_status': status,
        'current_platform': platform,
        'statuses': dict(GeneratedPost.STATUS_CHOICES),
    }
    
    return render(request, 'post_generator/post_list.html', context)

@login_required
def post_detail(request, pk):
    """View a specific post"""
    post = get_object_or_404(GeneratedPost, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = GeneratedPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Post updated successfully!')
            return redirect('post_detail', pk=post.pk)
    else:
        form = GeneratedPostForm(instance=post)
    
    context = {
        'post': post,
        'form': form,
    }
    
    return render(request, 'post_generator/post_detail.html', context)

@login_required
@require_POST
def post_delete(request, pk):
    """Delete a post"""
    post = get_object_or_404(GeneratedPost, pk=pk, user=request.user)
    post.delete()
    messages.success(request, 'Post deleted successfully!')
    return redirect('post_list')

@login_required
@require_POST
def post_publish(request, pk):
    """Publish a post (change status to published)"""
    post = get_object_or_404(GeneratedPost, pk=pk, user=request.user)
    post.status = 'published'
    post.save()
    messages.success(request, 'Post published successfully!')
    return redirect('post_detail', pk=post.pk)

def generate_post_image(template, variables, content):
    """Generate an image for the post based on the template and variables"""
    try:
        # Create a blank image
        width, height = 1200, 1200  # Default size
        image = Image.new('RGB', (width, height), color=template.background_color)
        draw = ImageDraw.Draw(image)
        
        # Try to load a font
        try:
            font_path = os.path.join('static', 'fonts', 'Roboto-Regular.ttf')
            font = ImageFont.truetype(font_path, 60)
            small_font = ImageFont.truetype(font_path, 40)
        except IOError:
            # Fallback to default font
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Draw the content
        text_color = template.text_color
        
        # Wrap text to fit the image
        lines = []
        words = content.split()
        line = ""
        for word in words:
            test_line = line + " " + word if line else word
            text_width = draw.textlength(test_line, font=font)
            if text_width < width - 100:
                line = test_line
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        
        # Draw the wrapped text
        y_position = 100
        for line in lines:
            draw.text((100, y_position), line, fill=text_color, font=font)
            y_position += 70
        
        # Add a watermark
        watermark = "Created with Social Media Post Generator"
        draw.text((100, height - 50), watermark, fill=text_color, font=small_font)
        
        # Save the image to a buffer
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Create a Django file object
        file_name = f"post_{template.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.png"
        return InMemoryUploadedFile(
            buffer, 
            None, 
            file_name, 
            'image/png', 
            buffer.getbuffer().nbytes, 
            None
        )
    
    except Exception as e:
        print(f"Error generating image: {e}")
        return None