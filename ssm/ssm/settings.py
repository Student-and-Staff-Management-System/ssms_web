"""
Django settings for ssm project.
"""
from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY=os.getenv('SECRET_KEY', 'django-insecure-fallback-key-for-dev-only')

DEBUG = True
ALLOWED_HOSTS = ['10.165.244.80', 'localhost', '127.0.0.1','*','13.126.152.167']


# --- APPLICATION DEFINITION ---
INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'ssm.apps.AuthConfig', # Replaces 'django.contrib.auth' to rename label
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'students',
    'staffs',
    'storages',  # For R2 storage backend
    'webpush',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'authentication',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'ssm.middleware.StaticFilesHeadersMiddleware',  # Custom middleware for static file headers
]

# Security settings that might block static files
SECURE_CONTENT_TYPE_NOSNIFF = False  # Allow CSS/JS to load properly
SECURE_BROWSER_XSS_FILTER = False  # Prevent XSS filter from blocking CSS

# Only use WhiteNoise in production (when DEBUG=False)
if not DEBUG:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

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


# DATABASES = {
#    "default": {
#        "ENGINE": "django.db.backends.postgresql",
#        "NAME": "ssm",
#        "USER": "postgres",
#       "PASSWORD": "dbms",
#        "HOST": "localhost",
#        "PORT": "5432",
#    }
# }

# DATABASES = {
#      'default': {
#          'ENGINE': 'django.db.backends.postgresql',
#          'NAME': os.getenv('DB_NAME'),
#          'USER': os.getenv('DB_USER'),                                                  
#          'PASSWORD': os.getenv('DB_PASSWORD'),
#          'HOST': os.getenv('DB_HOST'),
#          'PORT': os.getenv('DB_PORT'),
#      }
#  }
                                    

# Database Configuration
# Tries to use DATABASE_URL from environment first (for production/Render)
# Falls back to local PostgreSQL if not found.

if os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": dj_database_url.config(
            default=os.environ.get("DATABASE_URL"),
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    # Local Database Settings
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "ssm",
            "USER": "postgres",
            "PASSWORD": "dbms",
            "HOST": "localhost",
            "PORT": "5432",
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
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# --- STATIC FILES (for CSS, JS of your project and admin) ---

STATIC_URL = '/static/'

STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# --- REST FRAMEWORK & JWT CONFIGURATION ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
       'rest_framework.permissions.IsAuthenticated',
    ),
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15), # Web Users (Short)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=90),   # Mobile Users (Long)
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}


# Fix for Windows MIME types issues - CRITICAL for admin CSS
import mimetypes
# Ensure CSS and JS files are recognized with correct MIME types
mimetypes.add_type("text/css", ".css", True)
mimetypes.add_type("text/css", ".css", False)  # Also add without strict
mimetypes.add_type("application/javascript", ".js", True)
mimetypes.add_type("application/javascript", ".js", False)
mimetypes.add_type("text/javascript", ".js", True)

# --- STATIC FILES CONFIGURATION ---
# This tells Django where to look for your main static files folder.
if os.path.exists(os.path.join(BASE_DIR, 'static')):
    STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
else:
    STATICFILES_DIRS = []

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Ensure default static files finders are used (includes admin static files)
# This is the default, but we're being explicit to ensure admin files are found
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Only set storage in production (WhiteNoise)
# DO NOT set STATICFILES_STORAGE in development - let Django use defaults
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
# --- MEDIA FILES (for user-uploaded content) ---
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ==========================================
# CLOUDFLARE R2 STORAGE CONFIGURATION
# ==========================================


# ============================================================================
# CLOUDFLARE R2 STORAGE CONFIGURATION
# ============================================================================
# NOTE: Variable names use "AWS_*" prefix because Cloudflare R2 is S3-compatible.
# The django-storages library requires these exact variable names.
# Your files are stored in CLOUDFLARE R2, NOT AWS S3!
# ============================================================================

# R2 Storage Settings (using S3-compatible API)
AWS_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID')  # From Cloudflare R2
AWS_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY')  # From Cloudflare R2
AWS_STORAGE_BUCKET_NAME = os.getenv('R2_BUCKET_NAME')  # Your R2 bucket name
AWS_S3_ENDPOINT_URL = os.getenv('R2_ENDPOINT_URL')  # Points to Cloudflare, not AWS
AWS_S3_REGION_NAME = 'auto'  # R2 uses 'auto' for region
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None  # R2 doesn't use ACLs
AWS_QUERYSTRING_AUTH = False  # Don't add auth params to URLs


from urllib.parse import urlparse
import os

raw_public_url = os.getenv('R2_PUBLIC_URL')

if raw_public_url:
    raw_public_url = raw_public_url.strip().strip("'").strip('"')

    parsed = urlparse(raw_public_url)

    if parsed.scheme:
        raw_public_url = parsed.netloc
    else:
        raw_public_url = raw_public_url.lstrip('/')

AWS_S3_CUSTOM_DOMAIN = raw_public_url

# print(f"DEBUG: AWS_S3_CUSTOM_DOMAIN set to: '{AWS_S3_CUSTOM_DOMAIN}'")

# Use R2 for default file storage
# STORAGES Configuration (Django 4.2+)
STORAGES = {
    "default": {
        "BACKEND": "ssm.storage_backends.R2Storage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

if not DEBUG:
    STORAGES["staticfiles"]["BACKEND"] = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# --- DEFAULT SETTINGS ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CORS_ALLOWED_ORIGINS = ["null"]

# ==========================================
# EMAIL CONFIGURATION - GMAIL SMTP
# ==========================================

# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 465
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
# EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')

# --- GMAIL API CONFIGURATION ---
EMAIL_BACKEND = 'gmailapi_backend.mail.GmailBackend'

# Load credentials from gmail.json if it exists
GMAIL_CREDENTIALS_FILE = os.path.join(BASE_DIR, 'gmail.json')
if os.path.exists(GMAIL_CREDENTIALS_FILE):
    import json
    with open(GMAIL_CREDENTIALS_FILE, 'r') as f:
        gmail_creds = json.load(f)
        GMAIL_API_CLIENT_ID = gmail_creds.get('client_id')
        GMAIL_API_CLIENT_SECRET = gmail_creds.get('client_secret')
        GMAIL_API_REFRESH_TOKEN = gmail_creds.get('refresh_token')
else:
    # Fallback to environment variables or empty (will cause error if used)
    GMAIL_API_CLIENT_ID = os.getenv('GMAIL_API_CLIENT_ID')
    GMAIL_API_CLIENT_SECRET = os.getenv('GMAIL_API_CLIENT_SECRET')
    GMAIL_API_REFRESH_TOKEN = os.getenv('GMAIL_API_REFRESH_TOKEN')

DEFAULT_FROM_EMAIL = os.getenv('EMAIL_HOST_USER')



JAZZMIN_SETTINGS = {
    "site_title": "Annamalai University Admin",
    "site_header": "Annamalai University",
    "site_brand": "Annamalai University",
    "site_logo": "imgs/annamalai.png",
    "login_logo": "imgs/annamalai.png",
    "login_logo_dark": "imgs/annamalai.png",
    "site_logo_classes": "img-circle",
    "site_icon": "imgs/annamalai.png",
    "welcome_sign": "Welcome to the Admin Portal",
    "copyright": "Annamalai University",
    "search_model": ["students.Student", "auth.User"],
    "user_avatar": None,
    # Top Menu
    "topmenu_links": [
        {"name": "Home",  "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Audits / Logs", "url": "admin:staffs_auditlog_changelist", "permissions": ["staffs.view_auditlog"]},
        {"name": "Main Site", "url": "/", "new_window": True},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "students.Student": "fas fa-user-graduate",
        "staffs.Staff": "fas fa-chalkboard-teacher",
        "staffs.AuditLog": "fas fa-clipboard-list",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": False,
    "custom_css": "css/custom_admin.css",
    "custom_js": None,
    "use_google_fonts_cdn": True,
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {"auth.user": "collapsible", "auth.group": "vertical_tabs"},
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-teal",  # Matches the teal theme
    "accent": "accent-teal",
    "navbar": "navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-light-teal", # Light sidebar with teal accents
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "flatly", # Clean modern theme
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}


# ==========================================
# WEBPUSH CONFIGURATION (VAPID)
# ==========================================
WEBPUSH_SETTINGS = {
    "VAPID_PUBLIC_KEY": "BEw6LWC0G64ByqHYGlJl7+Uuzp4E3MCGiENIkLEp3Kr228uOv/92V/LhXSyWZ1CSUzT135/8QuTOyfHbSW8gjA==",
    "VAPID_PRIVATE_KEY": "NW2zAzsXXWh+mJK3ZqLeTXSItIEJ+icI0+7Z/pRAmrI=",
    "VAPID_ADMIN_EMAIL": "admin@annamalai.edu"
}

