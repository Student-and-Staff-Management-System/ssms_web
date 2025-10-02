"""
Django settings for ssm project.
"""
from pathlib import Path
import os

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-h)g6-a+cdh^rhpxsfhi5#8#a=++iq0z%*61-l%$nh6$^9e+r#s'
DEBUG = True
ALLOWED_HOSTS = ['10.165.244.80', 'localhost', '127.0.0.1','*','401dea466adf.ngrok-free.app']


# --- APPLICATION DEFINITION ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'students',
    'staffs',
    "anymail",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ssm.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ssm.wsgi.application'

# --- DATABASE ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'students',
        'USER': 'root',
        'PASSWORD': 'dbms',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}

# --- PASSWORD VALIDATION ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- INTERNATIONALIZATION ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --- STATIC FILES (for CSS, JS of your project and admin) ---
STATIC_URL = 'static/'

# --- ADD THIS LINE ---
# This tells Django where to look for your main static files folder.
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# --- MEDIA FILES (for user-uploaded content) ---
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# --- DEFAULT SETTINGS ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CORS_ALLOWED_ORIGINS = ["null"]

# settings.py

# your_project/settings.py

# Add this for development/testing
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# For production, you would use a real SMTP server:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.example.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your-email@example.com'
# EMAIL_HOST_PASSWORD = 'your-email-password'
#login_url = '/students/login/'

EMAIL_BACKEND = "anymail.backends.mailersend.EmailBackend"

ANYMAIL = {
    "MAILERSEND_API_KEY": "mlsn.09e6953347b2c58ed3ce196b960a7b2a75fd8c57fc541cd8a483895a077cc82d",
}

# Default from email
DEFAULT_FROM_EMAIL = "test-z0vklo6r391l7qrx.mlsender.net"
#LOGIN_URL = 'student_login'