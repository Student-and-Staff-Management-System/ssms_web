from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from .serializers import CustomTokenObtainPairSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
             return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)
             
        data = serializer.validated_data
        
        # Determine Client Type
        client_type = request.headers.get('X-Client-Type', 'web').lower()
        
        response = Response(data, status=status.HTTP_200_OK)

        if client_type == 'web':
            # For Web: Set tokens in HTTP-only cookies
            # Secure=False for dev (HTTP), True for prod (HTTPS - handled by settings usually but explicit here for clarity)
            # SameSite='Lax' ensures cookies are sent on top-level navigations
            
            # Access Token Cookie
            response.set_cookie(
                key='access_token',
                value=data['access'],
                httponly=True,
                secure=False,  # Set to True in production
                samesite='Lax',
                max_age=30 * 60  # 30 minutes
            )
            
            # Refresh Token Cookie
            response.set_cookie(
                key='refresh_token',
                value=data['refresh'],
                httponly=True,
                secure=False, # Set to True in production
                samesite='Lax',
                max_age=24 * 60 * 60 # 1 Day (matches logic in serializer)
            )
            
            # Remove tokens from response body for extra security on web?
            # Often good practice, but client might need them for local storage or immediate header usage. 
            # Keeping them in body + cookies is fine for hybrid approaches.
            
        return response

class LogoutView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                 # Try to get from cookie if not in body
                 refresh_token = request.COOKIES.get('refresh_token')
            
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            response = Response({"detail": "Successfully logged out."}, status=status.HTTP_205_RESET_CONTENT)
            
            # Clear Cookies (for Web)
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
            
            return response
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
