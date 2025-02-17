from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
import os
import logging
from django.views.decorators.csrf import ensure_csrf_cookie
import json
from django.template.loader import get_template
from django.views.decorators.cache import never_cache
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from .fastapi_app.rag.hybrid_rag import HybridRAG
from .fastapi_app.services.websearch_service import WebSearchService
from .services.email_service import EmailService
from .fastapi_app.rag.rag_service import RAGService
from django.views.decorators.csrf import csrf_protect
from software_auction.fastapi_app.services.knowledge_service import KnowledgeService
from openai import OpenAI
import tempfile
from django.middleware.csrf import get_token
import io
import ffmpeg
from .services.analysis_service import AnalysisService
from software_auction.fastapi_app.services.transcription_service import TranscriptionService
import uuid

logger = logging.getLogger(__name__)

# Define knowledge base directory
KNOWLEDGE_BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 
    'knowledge_base'
)

# Add to existing imports
analysis_service = AnalysisService()
transcription_service = TranscriptionService()

@never_cache  # Add this decorator
def index(request):
    return render(request, 'index.html')

@csrf_protect
@require_http_methods(["POST"])
def generate_and_send_email(request):
    try:
        # Parse JSON data with error handling
        try:
            data = json.loads(request.body)
            transcript = data.get('transcript', '').strip()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {request.body}")
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)

        if not transcript:
            return JsonResponse({
                'status': 'error',
                'message': 'No transcript provided'
            }, status=400)

        # Generate email content
        try:
            email_service = EmailService()
            email_content = email_service.generate_email(transcript)
            
            return JsonResponse({
                'status': 'success',
                'email': email_content
            })
        except Exception as e:
            logger.error(f"Error generating email: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'Error generating email: {str(e)}'
            }, status=500)

    except Exception as e:
        logger.error(f"Server error in generate_and_send_email: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }, status=500)

@require_http_methods(["GET"])
def health_check(request):
    """Simple health check endpoint"""
    try:
        return JsonResponse({
            'status': 'healthy',
            'message': 'Server is running'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=500)

@csrf_protect
@require_http_methods(["POST"])
def enrich_knowledge_base(request):
    """Enrich knowledge base with content"""
    return RAGService.handle_enrich_knowledge_base(request)

@require_http_methods(["GET"])
def inspect_knowledge_base(request):
    return RAGService.handle_inspect_knowledge_base(request)

@require_http_methods(["POST"])
def clear_knowledge_base(request):
    return RAGService.handle_clear_knowledge_base(request)

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
def generate_insights(request):
    try:
        data = json.loads(request.body)
        transcript = data.get('transcript', '')
        
        if not transcript:
            return JsonResponse({
                'status': 'error',
                'error': 'No transcript provided'
            })

        # Initialize HybridRAG with existing knowledge base
        hybrid_rag = HybridRAG()
        
        # Generate insights using RAG
        result = hybrid_rag.generate_insights(transcript)
        
        if 'error' in result:
            logger.error(f"Error in generate_insights: {result['error']}")
            return JsonResponse({
                'status': 'error',
                'error': result['error']
            }, status=500)
        
        # Log successful insight generation
        logger.info(f"Generated insights with confidence: {result.get('confidence', 0)}")
        
        return JsonResponse({
            'status': 'success',
            'insights': result.get('insights', ''),
            'confidence': result.get('confidence', 0),
            'sources': result.get('sources', [])
        })
        
    except Exception as e:
        logger.error(f"Error generating insights: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)
    
@require_http_methods(["POST"])
@ensure_csrf_cookie
def generate_summary(request):
    try:
        data = json.loads(request.body)
        transcription = data.get('transcript', '')
        
        hybrid_rag = HybridRAG()
        result = hybrid_rag.generate_summary(transcription)
        
        if 'error' in result:
            logger.error(f"Error in generate_summary: {result['error']}")
            return JsonResponse({'error': result['error']}, status=500)
            
        logger.info(f"Generated summary with confidence: {result.get('confidence', 0)}")
        
        return JsonResponse({
            'summary': result.get('summary', ''),
            'confidence': result.get('confidence', 0),
            'sources': result.get('sources', [])
        })
        
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["POST"])
def search_knowledge(request):
    try:
        # Get search query from request body
        data = json.loads(request.body)
        query = data.get('query', '')
        
        print(f"\nReceived search request for query: {query}")
        
        if not query:
            print("Empty query received")
            return JsonResponse({
                'status': 'error',
                'error': 'No search query provided'
            })
        
        # Create WebSearcher instance and perform search
        searcher = WebSearchService()
        print("Created WebSearcher instance")
        
        # Get search results
        results = searcher.search_and_process(query)
        print(f"Search results from WebSearcher: {results}")
        
        # Return results as JSON response
        response_data = {
            'status': 'success',
            'results': results if results else []  # Ensure we always send an array
        }
        print(f"Sending response: {response_data}")
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"Error in search_knowledge: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)

@require_http_methods(["POST"])
def add_website_to_knowledge_base(request):
    """Add a single website to knowledge base with summary and content type analysis"""
    try:
        data = json.loads(request.body)
        result = data.get('result')
        
        if not result:
            return JsonResponse({
                'status': 'error',
                'message': 'No result provided'
            })
            
        knowledge_service = KnowledgeService()
        
        # Process single result
        enriched_results = knowledge_service.enrich_from_search_results([result], "manual_addition")
        
        if enriched_results and enriched_results[0].get('added_to_kb'):
            return JsonResponse({
                'status': 'success',
                'message': f'Successfully added "{result["title"]}" to knowledge base'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to add result to knowledge base'
            })
            
    except Exception as e:
        logger.error(f"Error adding to knowledge base: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@csrf_protect
@require_http_methods(["POST"])
def transcribe_whisper(request):
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        logger.info(f"API key present: {bool(api_key)}")
        
        if not api_key:
            logger.error("OpenAI API key not found in environment variables")
            return JsonResponse({
                'status': 'error',
                'error': 'OpenAI API key not configured'
            }, status=500)

        if 'audio' not in request.FILES:
            logger.error("No audio file in request")
            return JsonResponse({
                'status': 'error',
                'error': 'No audio file received'
            }, status=400)
            
        audio_file = request.FILES['audio']
        logger.info(f"Received audio file: {audio_file.name}, size: {audio_file.size} bytes, content_type: {audio_file.content_type}")

        try:
            # Initialize OpenAI client
            client = OpenAI()
            
            # Convert InMemoryUploadedFile to bytes-like object
            audio_content = audio_file.read()
            
            # Create a file-like object
            audio_io = io.BytesIO(audio_content)
            audio_io.name = 'audio.wav'  # OpenAI needs a filename
            
            # Send audio file to OpenAI API
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_io,
                response_format="text"
            )
            
            # Convert response to string
            transcript_text = str(response)
            
            logger.info("Successfully transcribed audio chunk")
            return JsonResponse({
                'status': 'success',
                'transcript': transcript_text
            })
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            logger.exception("Full traceback:")
            return JsonResponse({
                'status': 'error',
                'error': f"OpenAI API error: {str(e)}"
            }, status=500)
            
    except Exception as e:
        logger.error(f"Server error in transcribe_whisper: {str(e)}")
        logger.exception("Full traceback:")
        return JsonResponse({
            'status': 'error',
            'error': f"Server error: {str(e)}"
        }, status=500)

@csrf_protect
@require_http_methods(["POST"])
def generate_analysis_instructions(request):
    try:
        data = json.loads(request.body)
        transcript = data.get('transcript', '')
        use_llama = data.get('use_llama', False)  # Get model preference from request
        
        result = analysis_service.generate_analysis_instructions(transcript, use_llama)
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in generate_analysis_instructions: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)

def handle_transcription_request(request):
    # Logic to handle transcription request
    audio_file = request.FILES.get('audio')
    result = transcription_service.transcribe_audio(audio_file)
    return JsonResponse(result)

@csrf_protect
def get_session_token(request):
    """Generate a session token for WebRTC"""
    try:
        token = str(uuid.uuid4())
        return JsonResponse({
            'status': 'success',
            'token': token
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
