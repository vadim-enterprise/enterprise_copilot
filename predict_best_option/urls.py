from django.contrib import admin 
from django.urls import path 
from . import views 
  
urlpatterns = [
    path('admin/', admin.site.urls, name='admin'),     
    path('', views.index, name='index'),
    path('reset-conversation/', views.reset_conversation, name='reset_conversation'),
    path('generate-insights/', views.generate_insights, name='generate_insights'),
    path('generate-send-email/', views.generate_and_send_email, name='generate_and_send_email'),
]