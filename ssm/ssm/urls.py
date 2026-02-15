"""
URL configuration for ssm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# Customize admin site
admin.site.site_header = "Annamalai University"
admin.site.site_title = "AU Admin Portal"
admin.site.index_title = "Department of IT - Administration"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('students.urls')),
    path('staffs/', include('staffs.urls')),
    path('api/auth/', include('authentication.urls')),
    path('webpush/', include('webpush.urls')),  # Added webpush URLS
    path('sw.js', TemplateView.as_view(template_name='sw.js', content_type='application/javascript'), name='sw.js'),
    path('.well-known/assetlinks.json', TemplateView.as_view(template_name='assetlinks.json', content_type='application/json'), name='assetlinks'),
    path('offline/', TemplateView.as_view(template_name='offline.html'), name='offline_page'),
]

# Serve static files in development
if settings.DEBUG:
    # Serve static files (including admin static files)
    # staticfiles_urlpatterns() uses Django's static file finders to locate files
    # from all apps (including django.contrib.admin)
    urlpatterns += staticfiles_urlpatterns()
    
    # Serve media files
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
