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
        email = sociallogin.account.extra_data.get('email')
        if not email:
            return
        # email exist
        try:
            user = User.objects.get(email=email)
            
            # no socially connected
            if not sociallogin.is_existing:
                # Connect this social account to existing user
                sociallogin.connect(request, user)
                
        except User.DoesNotExist:
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
        
        return user