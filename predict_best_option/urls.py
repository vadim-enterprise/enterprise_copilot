from django.contrib import admin 
from django.urls import path 
from . import views 
  
urlpatterns = [
    path('admin/', admin.site.urls, name='admin'),     
    path('', views.index, name='index'),
    path('reset-conversation/', views.reset_conversation, name='reset_conversation'),
    path('generate-insights/', views.generate_insights, name='generate_insights'),
    path('generate-send-email/', views.generate_and_send_email, name='generate_and_send_email'),
    path('inspect-knowledge-base/', views.inspect_knowledge_base, name='inspect-knowledge-base'),
    path('search-knowledge/', views.search_knowledge, name='search-knowledge'),
    path('health-check/', views.health_check, name='health_check'),
    path('clear-knowledge-base/', views.clear_knowledge_base, name='clear_knowledge_base'),
    path('enrich-knowledge-base/', views.enrich_knowledge_base, name='enrich_knowledge_base'),
    path('add-website-to-knowledge-base/', views.add_website_to_knowledge_base, name='add_website_to_knowledge_base'),
]