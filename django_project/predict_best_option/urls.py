from django.contrib import admin 
from django.urls import path 
from . import views 
  
urlpatterns = [
    path('admin/', admin.site.urls, name='admin'),     
    path('', views.index, name='index'),
    path('process_audio/', views.process_audio, name='process_audio'),
]