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
    path('generate-email/', views.generate_and_send_email, name='generate_email'),
    path('enrich-knowledge-base/', views.enrich_knowledge_base, name='enrich_knowledge_base'),
    path('inspect-knowledge-base/', views.inspect_knowledge_base, name='inspect_knowledge_base'),
    path('clear-knowledge-base/', views.clear_knowledge_base, name='clear_knowledge_base'),
    path('search-knowledge/', views.search_knowledge, name='search_knowledge'),
    path('add-website-to-knowledge-base/', views.add_website_to_knowledge_base, name='add_website_to_knowledge_base'),
    path('reset-conversation/', views.reset_conversation, name='reset_conversation'),
    path('health-check/', views.health_check, name='health_check'),
    path('generate-analysis-instructions/', views.generate_analysis_instructions, name='generate_analysis_instructions'),
    path('generate-speech/', views.handle_tts_request, name='generate_speech'),
    path('transcribe-speech/', views.handle_transcription_request, name='transcribe_speech'),
]

def handle_tts_request(request):
    # Logic to handle TTS request
    text = request.POST.get('text')
    voice = request.POST.get('voice', 'alloy')

    if not text:
        return JsonResponse({'status': 'error', 'message': 'Text is required.'}, status=422)

    result = tts_service.generate_speech(text, voice)
    return JsonResponse(result)

def call_model(self, summarized_data):
    prompt = f"Based on the following information, provide a concise answer: {summarized_data}"
    # Call your model with the prompt
    return model_response
