"""
Django settings for ssm project.
"""
from pathlib import Path
import os
import dj_database_url
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-h)g6-a+cdh^rhpxsfhi5#8#a=++iq0z%*61-l%$nh6$^9e+r#s'
DEBUG = True
ALLOWED_HOSTS = ['10.165.244.80', 'localhost', '127.0.0.1','*']


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
    "anymail",
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

# --- DATABASE ---
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


# CRITICAL FOR RENDER:
# If Render provides a 'DATABASE_URL' (like for a Managed Postgres DB),
# this line overrides the MySQL settings above automatically.

# ...
if 'DATABASE_URL' in os.environ:
    DATABASES['default'] = dj_database_url.config(conn_max_age=600, ssl_require=True)
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
STATIC_URL = '/static/'

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

# --- DEFAULT SETTINGS ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CORS_ALLOWED_ORIGINS = ["null"]

# settings.py

# your_project/settings.py

# Add this for development/testing
#EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
# For production, you would use a real SMTP server:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.example.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your-email@example.com'
# EMAIL_HOST_PASSWORD = 'your-email-password'
#login_url = '/students/login/'

# EMAIL_BACKEND = "anymail.backends.mailersend.EmailBackend"

# ANYMAIL = {
#     "MAILGUN_API_KEY": "",
#     "MAILGUN_SENDER_DOMAIN": "sandboxb5c88b3d41574fd2b90292f18775d58e.mailgun.org",  # e.g., mg.yourdomain.com
# }
# # Default from email
# DEFAULT_FROM_EMAIL = "sandboxb5c88b3d41574fd2b90292f18775d58e.mailgun.org" 
# SERVER_EMAIL = "sandboxb5c88b3d41574fd2b90292f18775d58e.mailgun.org" # For error reports
# #LOGIN_URL = 'student_login'

# # settings.py
# from decouple import config

# # Email Configuration with Mailgun
# EMAIL_BACKEND = 'anymail.backends.mailgun.EmailBackend'
# ANYMAIL = {
#     #"MAILGUN_API_KEY": config("774826f10a768fc1a4ca2d5b753e4c5d-8b22cbee-45c2a532"),  # Your Mailgun API key
#     "MAILGUN_SENDER_DOMAIN": config('sandboxb5c88b3d41574fd2b90292f18775d58e.mailgun.org'),
# }
# DEFAULT_FROM_EMAIL = config('sam@sandboxb5c88b3d41574fd2b90292f18775d58e.mailgun.org', default='rash@sandboxb5c88b3d41574fd2b90292f18775d58e.mailgun.org')
# SERVER_EMAIL = DEFAULT_FROM_EMAIL

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
GEMINI_API_KEY = "AIzaSyCWO00b15Lh5ig-HWpDFNoT35MdLLiRwNQ"
