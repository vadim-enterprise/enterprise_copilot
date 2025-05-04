from django.urls import path
from . import views
from software_auction.fastapi_app.services.tts_service import TTSService
from software_auction.fastapi_app.services.transcription_service import TranscriptionService
from django.http import JsonResponse

app_name = 'software_auction'

urlpatterns = [
    path('', views.index, name='index'),
    path('transcribe-whisper/', views.transcribe_whisper, name='transcribe_whisper'),
    path('generate-insights/', views.generate_insights, name='generate_insights'),
    path('enrich-knowledge-base/', views.enrich_knowledge_base, name='enrich_knowledge_base'),
    path('inspect-knowledge-base/', views.inspect_knowledge_base, name='inspect_knowledge_base'),
    path('clear-knowledge-base/', views.clear_knowledge_base, name='clear_knowledge_base'),
    path('search-knowledge/', views.search_knowledge, name='search_knowledge'),
    path('add-website-to-knowledge-base/', views.add_website_to_knowledge_base, name='add_website_to_knowledge_base'),
    path('reset-conversation/', views.reset_conversation, name='reset_conversation'),
    path('health-check/', views.health_check, name='health_check'),
    path('generate-analysis-instructions/', views.generate_analysis_instructions, name='generate_analysis_instructions'),
    path('transcribe-speech/', views.handle_transcription_request, name='transcribe_speech'),
]

