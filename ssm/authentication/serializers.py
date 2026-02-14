from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings
from django.contrib.auth.models import update_last_login
from datetime import timedelta

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['role'] = getattr(user, 'role', 'student') # Default to student if no role
        if hasattr(user, 'is_staff'):
             token['is_staff'] = user.is_staff
             
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Detect Client Type
        request = self.context['request']
        client_type = request.headers.get('X-Client-Type', 'web').lower()
        
        # Add client type to response data for debugging/verification
        data['client_type'] = client_type

        # Customize Token Lifetime based on Client Type
        refresh = self.get_token(self.user)
        
        if client_type == 'mobile':
            # Long-lived token for mobile (e.g., 90 days)
            # Note: The refresh token itself has the expiry claim. 
            # We are verifying the lifetime is set correctly in settings.
            # SimpleJWT uses settings.REFRESH_TOKEN_LIFETIME by default.
            # If we wanted to override per-request, we'd need to manually set the exp claim 
            # on the refresh object, but it's cleaner to rely on the default long lifetime 
            # configured in settings for "refresh" tokens which are intended for long sessions.
            pass 
            
        elif client_type == 'web':
             # Short-lived session for web. 
             # We might want to enforce a shorter refresh token lifetime for web if needed,
             # but typically web uses the Access Token (short) and rotates the Refresh token.
             # If strict security is needed, we can manually set a shorter exp on the refresh token here.
             
             # Example: Force web refresh token to expire in 24 hours instead of 90 days
             refresh.set_exp(lifetime=timedelta(days=1))
        
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)

        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)

        return data
