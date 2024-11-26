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
from azure.identity import ClientSecretCredential
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
import json
import logging
import requests

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

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prompts')

def load_prompt(filename):
    """Load a prompt file from the prompts directory."""
    try:
        file_path = os.path.join(PROMPTS_DIR, filename)
        logger.info(f"Attempting to load prompt file: {file_path}")
        
        # Check if directory exists
        if not os.path.exists(PROMPTS_DIR):
            logger.error(f"Prompts directory not found: {PROMPTS_DIR}")
            raise FileNotFoundError(f"Prompts directory not found: {PROMPTS_DIR}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"Prompt file not found: {file_path}")
            raise FileNotFoundError(f"Prompt file not found: {file_path}")
        
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            logger.info(f"Successfully loaded prompt file: {filename}")
            return content
    except Exception as e:
        logger.error(f"Error loading prompt file {filename}: {str(e)}")
        raise
            

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
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
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
        # Load prompts first
        summary_prompt = load_prompt('summary_prompt.txt')
        insights_prompt = load_prompt('insights_prompt.txt')
    except Exception as e:
        logger.error(f"Failed to load prompt files: {str(e)}")
        return JsonResponse({
            'error': f'Failed to load prompt files: {str(e)}'
        }, status=500)

    # Parse request data
    try:
        data = json.loads(request.body)
        transcription = data.get('transcription', '')
        
        logger.info(f"Generating insights for transcription of length {len(transcription)}")

        if not transcription:
            return JsonResponse({
                'error': 'Missing transcription'
            }, status=400)

        # Initialize OpenAI client
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Generate summary
        summary = ask_chatgpt(client, f"""
            {summary_prompt}
            
            Conversation:
            {transcription}
        """)

        # Generate insights
        insights = ask_chatgpt(client, f"""
            {insights_prompt}
            
            Conversation:
            {transcription}
        """)

        logger.debug(f"Summary generated: {summary[:100]}...")
        logger.debug(f"Insights generated: {insights[:100]}...")

        return JsonResponse({
            'summary': summary,
            'insights': insights
        })

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return JsonResponse({
            'error': f'Invalid JSON format: {str(e)}'
        }, status=400)
    except Exception as e:
        logger.error(f"Error generating insights: {str(e)}")
        return JsonResponse({
            'error': f'Error generating insights: {str(e)}'
        }, status=500)

@require_http_methods(["POST"])
@ensure_csrf_cookie
def reset_conversation(request):
    try:
        # Clear any session data if needed
        if 'conversation_history' in request.session:
            del request.session['conversation_history']
        
        return JsonResponse({
            'status': 'success',
            'message': 'Conversation reset successfully'
        })
    except Exception as e:
        logger.error(f"Error in reset_conversation: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

logger = logging.getLogger(__name__)

@require_http_methods(["POST"])
@ensure_csrf_cookie
def generate_and_send_email(request):
    try:
        data = json.loads(request.body)
        transcription = data.get('transcription', '')
        
        if not transcription:
            return JsonResponse({
                'error': 'Missing transcription'
            }, status=400)

        # Initialize OpenAI client for content generation
        openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Generate email content using GPT
        email_prompt = load_prompt('email_prompt.txt')
        response = ask_chatgpt(openai_client, f"""
            {email_prompt}
            
            Conversation:
            {transcription}
            
            Please generate a professional email based on this conversation.
            Format the response as JSON with "to", "subject", and "body" fields.
        """)

        try:
            # Parse the email content
            email_data = json.loads(response)
            
            # Initialize Microsoft Graph client
            credentials = ClientSecretCredential(
                tenant_id=settings.MS_TENANT_ID,
                client_id=settings.MS_CLIENT_ID,
                client_secret=settings.MS_CLIENT_SECRET
            )
            
            graph_client = GraphClient(credential=credentials)

            # Prepare email message
            message = {
                "message": {
                    "subject": email_data.get('subject', 'Meeting Follow-up'),
                    "body": {
                        "contentType": "HTML",
                        "content": email_data.get('body', '')
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": email_data.get('to', '')
                            }
                        }
                    ]
                },
                "saveToSentItems": "true"
            }

            # Send draft email
            result = graph_client.post(
                '/me/messages',
                data=message,
                headers={'Content-Type': 'application/json'}
            )

            if result.status_code == 201:
                response_data = result.json()
                return JsonResponse({
                    'status': 'success',
                    'message': 'Email draft created successfully',
                    'email_data': {
                        'to': email_data.get('to', ''),
                        'subject': email_data.get('subject', ''),
                        'body': email_data.get('body', ''),
                        'message_id': response_data.get('id')
                    }
                })
            else:
                raise Exception(f"Failed to create draft: {result.text}")

        except json.JSONDecodeError:
            logger.error("Failed to parse GPT response as JSON")
            return JsonResponse({
                'error': 'Failed to generate proper email format'
            }, status=500)
            
        except Exception as e:
            logger.error(f"Error in Microsoft Graph API: {str(e)}")
            return JsonResponse({
                'error': f'Failed to create email draft: {str(e)}'
            }, status=500)

    except Exception as e:
        logger.error(f"Error generating email: {str(e)}")
        return JsonResponse({
            'error': f'Error generating email: {str(e)}'
        }, status=500)