# post_generator/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import PostTemplate, GeneratedPost, UserProfile
import json

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            UserProfile.objects.create(user=user)
        return user

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('bio', 'preferred_platforms', 'default_hashtags')
        widgets = {
            'preferred_platforms': forms.CheckboxSelectMultiple(),
            'default_hashtags': forms.TextInput(attrs={'placeholder': 'e.g., #marketing #socialmedia'})
        }

class PostTemplateForm(forms.ModelForm):
    variables_json = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': '{"company_name": "Your company name", "offer": "Special offer description"}'}),
        help_text="Enter variables as a JSON object",
        required=False
    )
    
    class Meta:
        model = PostTemplate
        fields = ('name', 'category', 'template_text', 'background_color', 'text_color', 'is_public')
        widgets = {
            'template_text': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Check out our new {product} at {company_name}!'}),
            'background_color': forms.TextInput(attrs={'type': 'color'}),
            'text_color': forms.TextInput(attrs={'type': 'color'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['variables_json'].initial = json.dumps(self.instance.variables, indent=2)
    
    def clean_variables_json(self):
        variables_json = self.cleaned_data.get('variables_json', '{}')
        if not variables_json:
            return {}
        
        try:
            return json.loads(variables_json)
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON format for variables")
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.variables = self.cleaned_data.get('variables_json', {})
        if commit:
            instance.save()
        return instance

class GeneratedPostForm(forms.ModelForm):
    class Meta:
        model = GeneratedPost
        fields = ('platform', 'template', 'content', 'image', 'status', 'schedule_time')
        widgets = {
            'schedule_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'content': forms.Textarea(attrs={'rows': 4}),
        }

class DynamicPostGeneratorForm(forms.Form):
    platform = forms.ModelChoiceField(queryset=None)
    template = forms.ModelChoiceField(queryset=None)
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Platform, PostTemplate
        
        self.fields['platform'].queryset = Platform.objects.all()
        self.fields['template'].queryset = PostTemplate.objects.filter(
            is_public=True
        ) | PostTemplate.objects.filter(created_by=user)
        
        self.user = user
        self.template_variables = {}
        
    def add_dynamic_fields(self, template_id):
        try:
            from .models import PostTemplate
            template = PostTemplate.objects.get(id=template_id)
            self.template_variables = template.variables
            
            for var_name, var_desc in template.variables.items():
                field_name = f"var_{var_name}"
                self.fields[field_name] = forms.CharField(
                    label=var_name.replace('_', ' ').title(),
                    help_text=var_desc,
                    required=True
                )
                
        except PostTemplate.DoesNotExist:
            pass