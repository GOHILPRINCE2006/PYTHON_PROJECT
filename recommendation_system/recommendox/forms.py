# recommendox/forms.py
from django import forms
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
        # Make duration not required by default
        self.fields['duration'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get('content_type')
        duration = cleaned_data.get('duration')
        
        # Custom validation based on content type
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
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)
