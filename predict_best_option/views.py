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

logger = logging.getLogger(__name__)

def index(request):
    return render(request, 'predict_best_option/index.html')

@require_http_methods(["GET", "POST"])
def process_audio(request):
    if request.method == 'POST':
        logger.info("Received POST request")
        try:
            audio_file = request.FILES.get('audio_file')
            company_description = request.POST.get('company_description')
            
            if not audio_file or not company_description:
                logger.error("Missing audio file or company description")
                return JsonResponse({"error": "Missing audio file or company description"}, status=400)

            logger.info(f"Received audio file: {audio_file.name}")
            logger.info(f"Audio file size: {audio_file.size} bytes")
            logger.info(f"Received company description: {company_description}")

            # Create a temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save the uploaded file to the temporary directory
                temp_audio_path = os.path.join(temp_dir, audio_file.name)
                with open(temp_audio_path, 'wb+') as destination:
                    for chunk in audio_file.chunks():
                        destination.write(chunk)

                logger.info(f"Saved audio file to: {temp_audio_path}")

                # Convert the audio to WAV format using pydub
                audio = AudioSegment.from_file(temp_audio_path)
                wav_path = os.path.join(temp_dir, 'converted_audio.wav')
                audio.export(wav_path, format="wav")

                logger.info(f"Converted audio to WAV: {wav_path}")

                # Transcribe the converted WAV file
                transcribed_text = transcribe_audio(wav_path)
                logger.info(f"Transcribed text: {transcribed_text}")

                # Initialize OpenAI client
                client = OpenAI(api_key=settings.OPENAI_API_KEY)

                # Generate the summary, insights, and recommendations
                summary_output = ask_chatgpt(client, f"Summarize the following text: {transcribed_text}")
                insights_output = ask_chatgpt(client, f"Provide key insights from the following text: {transcribed_text}")
                recommendations_output = ask_chatgpt(client, f"Based on this transcription and the company description: {company_description}, provide recommendations for the company")

                logger.info("Successfully processed audio and generated outputs")

                return JsonResponse({
                    'transcribed_text': transcribed_text,
                    'summary_output': summary_output,
                    'insights_output': insights_output,
                    'recommendations_output': recommendations_output,
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