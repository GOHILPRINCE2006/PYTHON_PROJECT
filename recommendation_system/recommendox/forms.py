# recommendox/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Content, Review

class ContentForm(forms.ModelForm):
    class Meta:
        model = Content
        fields = '__all__'
        widgets = {
            'release_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'cast': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['duration'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get('content_type')
        duration = cleaned_data.get('duration')
        
        if content_type == 'Movie' and not duration:
            self.add_error('duration', 'Duration is required for Movies')
        elif content_type == 'Web Series' and not duration:
            self.add_error('duration', 'Season information is required for Web Series')
        
        return cleaned_data
    
    def clean_poster_url(self):
        url = self.cleaned_data.get('poster_url')
        return url
    
    def clean_trailer_url(self):
        url = self.cleaned_data.get('trailer_url')
        return url


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['comment']


class UserRegistrationForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'})
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
      
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists. Please choose another.")
        if len(username) < 3:
            raise forms.ValidationError("Username must be at least 3 characters long.")
        
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already registered. Please use another email.")
     
        if '@' not in email:
            raise forms.ValidationError("Email must contain @ symbol.")
        
        try:
            local, domain = email.split('@')
        except ValueError:
            raise forms.ValidationError("Invalid email format.")
    
        if not local:
            raise forms.ValidationError("Email must have characters before @.")
    
        if '.' not in domain:
            raise forms.ValidationError("Domain must contain a dot (e.g., .com, .org).")
       
        domain_parts = domain.split('.')
        if len(domain_parts) < 2 or not domain_parts[0]:
            raise forms.ValidationError("Must have characters between @ and .")
       
        if len(domain_parts[-1]) < 2:
            raise forms.ValidationError("Domain extension must be at least 2 characters (e.g., .com, .in).")
        
        return email

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
    
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
       
        if not any(char.isdigit() for char in password):
            raise forms.ValidationError("Password must contain at least one digit (0-9).")
       
        if not any(char.isalpha() for char in password):
            raise forms.ValidationError("Password must contain at least one letter.")
        
        # if not any(char.isupper() for char in password):
        #     raise forms.ValidationError("Password must contain at least one uppercase letter.")
        
        # special_chars = "!@#$%^&*()_+-=[]{};':\"\\|,.<>/?`~"
        # if not any(char in special_chars for char in password):
        #     raise forms.ValidationError("Password must contain at least one special character.")
        
        return password
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        
        return password2

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Passwords do not match.")
        
        return cleaned_data