# recommendox/adapter.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.contrib import messages

User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter for pure Google login
    - Auto-links existing emails
    - No signup form
    - Direct login
    """
    
    def pre_social_login(self, request, sociallogin):
        """
        This runs BEFORE allauth processes the social login.
        We check if email exists and connect automatically.
        """
        # Get email from Google
        email = sociallogin.account.extra_data.get('email')
        if not email:
            return
        
        # Check if user exists with this email
        try:
            user = User.objects.get(email=email)
            
            # If user exists but social account not connected
            if not sociallogin.is_existing:
                # Connect this social account to existing user
                sociallogin.connect(request, user)
                
        except User.DoesNotExist:
            # New user - will be created automatically
            pass
    
    def is_open_for_signup(self, request, sociallogin):
        """
        Allow signup for social accounts only
        """
        return True
    
    def save_user(self, request, sociallogin, form=None):
        """
        Customize user creation
        """
        user = super().save_user(request, sociallogin, form)
        
        # You can add custom logic here
        # For example: set user as active, add to a group, etc.
        
        return user