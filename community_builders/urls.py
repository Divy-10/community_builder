"""
URL configuration for community_builders project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.views.generic.base import RedirectView
from django.http import Http404

def safe_serve(request, path, document_root=None, **kwargs):
    try:
        return serve(request, path, document_root, **kwargs)
    except (UnicodeError, ValueError, OSError):
        raise Http404("File not found or invalid filename encoding")

admin.site.site_header = "UniVo administration"
admin.site.site_title = "UniVo Admin Portal"
admin.site.index_title = "Welcome to UniVo Administration Portal"


urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url='/static/assets/images/logo.png')),
    path('admin/', admin.site.urls),
    path('custom-admin/', include('custom_admin.urls')),
    path('', include('user.urls')),
    re_path(r'^media/(?P<path>.*)$', safe_serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns+=static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
