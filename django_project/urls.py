"""
URL configuration for django_webapp project.

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
from django.conf import settings
from django.conf.urls.static import static
from software_auction.views import get_session_token

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', include('software_auction.urls')),
    path('api/get-session-token/', get_session_token, name='get_session_token'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
