from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import speech_recognition as sr
from openai import OpenAI
import openai
from pydub import AudioSegment
import os
import tempfile
import logging
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import ensure_csrf_cookie
import json
from django.template.loader import get_template
from django.views.decorators.cache import never_cache

logger = logging.getLogger(__name__)

@never_cache  # Add this decorator
def index(request):
    try:
        template = get_template('predict_best_option/index.html')
        logger.info(f"Loading template from: {template.origin.name}")
        response = render(request, 'predict_best_option/index.html')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    except Exception as e:
        logger.error(f"Error loading template: {str(e)}")
        raise

@require_http_methods(["GET", "POST"])
def process_audio(request):
    if request.method == 'POST':
        logger.info("Received POST request")
        try:
            audio_file = request.FILES.get('audio_file')
            
            if not audio_file:
                logger.error("Missing audio file")
                return JsonResponse({"error": "Missing audio file"}, status=400)

            logger.info(f"Received audio file: {audio_file.name}")
            logger.info(f"Audio file size: {audio_file.size} bytes")

            # Create a temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # ... rest of the audio processing code ...

                # Generate the summary and insights
                summary_output = ask_chatgpt(client, f"Summarize the following text: {transcribed_text}")
                insights_output = ask_chatgpt(client, f"Provide key insights from the following text: {transcribed_text}")

                logger.info("Successfully processed audio and generated outputs")

                return JsonResponse({
                    'transcribed_text': transcribed_text,
                    'summary_output': summary_output,
                    'insights_output': insights_output
                })

        except Exception as e:
            logger.exception(f"Error in process_audio: {str(e)}")
            return JsonResponse({"error": f"Server error: {str(e)}"}, status=500)

    return render(request, 'predict_best_option/index.html')

def transcribe_audio(file_path):
    logger.info(f"Starting audio transcription for file: {file_path}")
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio_data = recognizer.record(source)
    try:
        transcribed_text = recognizer.recognize_google(audio_data)
        logger.info("Audio transcription successful")
        return transcribed_text
    except sr.UnknownValueError:
        logger.warning("Could not understand audio")
        return "Could not understand audio."
    except sr.RequestError as e:
        logger.error(f"Could not request results from Google Speech Recognition service; {str(e)}")
        return "Could not request results from the speech recognition service."

def ask_chatgpt(client, prompt):
    logger.info(f"Sending request to ChatGPT with prompt: {prompt[:50]}...")  # Log first 50 chars of prompt
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1000
        )
        logger.info("Received response from ChatGPT")
        return response.choices[0].message.content
    except openai.APIError as e:
        logger.error(f"OpenAI API Error: {str(e)}")
        return f"OpenAI API Error: {str(e)}"
    except openai.APIConnectionError as e:
        logger.error(f"Failed to connect to OpenAI API: {str(e)}")
        return "Failed to connect to OpenAI API. Please check your internet connection."
    except openai.RateLimitError as e:
        logger.error(f"OpenAI API request exceeded rate limit: {str(e)}")
        return "OpenAI API request exceeded rate limit. Please try again later."
    except openai.AuthenticationError as e:
        logger.error(f"OpenAI API authentication error: {str(e)}")
        return "Authentication with OpenAI failed. Please check your API key."
    except openai.InvalidRequestError as e:
        logger.error(f"Invalid request to OpenAI API: {str(e)}")
        return f"Invalid request to OpenAI API: {str(e)}"
    except Exception as e:
        logger.exception(f"Unexpected error in ChatGPT API call: {str(e)}")
        return f"An unexpected error occurred: {str(e)}"
    
@require_http_methods(["POST"])
@ensure_csrf_cookie
def generate_insights(request):
    try:
        data = json.loads(request.body)
        transcription = data.get('transcription')

        if not transcription:
            return JsonResponse({
                'error': 'Missing transcription'
            }, status=400)

        # Initialize OpenAI client
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Generate insights directly from transcription
        insights = ask_chatgpt(client, f"""
            Analyze the following conversation and provide key insights and a brief summary:
            
            {transcription}
            
            Please format your response in a clear, concise manner.
            """)

        return JsonResponse({
            'insights': insights
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.exception('Error generating insights')
        return JsonResponse({
            'error': str(e)
        }, status=500)