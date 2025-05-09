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
from django.urls import path, re_path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
import json

def api_proxy(request, path):
    """Proxy requests to FastAPI server"""
    import requests
    fastapi_url = f"http://localhost:8000/api/{path}"
    response = requests.request(
        method=request.method,
        url=fastapi_url,
        headers={key: value for key, value in request.headers.items() if key != 'Host'},
        data=request.body,
        cookies=request.COOKIES,
    )
    return HttpResponse(
        content=response.content,
        status=response.status_code,
        content_type=response.headers.get('content-type', 'application/json')
    )

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
    path('transcribe-whisper/', TemplateView.as_view(template_name='index.html'), name='transcribe_whisper'),
    path('generate-insights/', TemplateView.as_view(template_name='index.html'), name='generate_insights'),
    path('enrich-knowledge-base/', TemplateView.as_view(template_name='index.html'), name='enrich_knowledge_base'),
    path('inspect-knowledge-base/', TemplateView.as_view(template_name='index.html'), name='inspect_knowledge_base'),
    path('clear-knowledge-base/', TemplateView.as_view(template_name='index.html'), name='clear_knowledge_base'),
    path('search-knowledge/', TemplateView.as_view(template_name='index.html'), name='search_knowledge'),
    path('add-website-to-knowledge-base/', TemplateView.as_view(template_name='index.html'), name='add_website_to_knowledge_base'),
    path('reset-conversation/', TemplateView.as_view(template_name='index.html'), name='reset_conversation'),
    path('health-check/', TemplateView.as_view(template_name='index.html'), name='health_check'),
    path('generate-analysis-instructions/', TemplateView.as_view(template_name='index.html'), name='generate_analysis_instructions'),
    path('transcribe-speech/', TemplateView.as_view(template_name='index.html'), name='transcribe_speech'),
    path('api/get-session-token/', TemplateView.as_view(template_name='index.html'), name='get_session_token'),
    re_path(r'^media/(?P<path>.*)$', TemplateView.as_view(template_name='index.html')),
    
    # Add FastAPI proxy routes
    re_path(r'^api/(?P<path>.*)$', api_proxy, name='api_proxy'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
