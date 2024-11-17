from django.urls import re_path
from . import transcription

websocket_urlpatterns = [
    re_path(r'ws/transcribe/$', transcription.Transcription.as_asgi()),
]