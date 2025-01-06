from django.shortcuts import render
from django.http import JsonResponse
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
from .hybrid_rag import HybridRAG
from .web_search import WebSearcher
from .services.email_service import EmailService
from .services.rag_service import RAGService
from django.views.decorators.csrf import csrf_protect
from .services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)

# Define knowledge base directory
KNOWLEDGE_BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 
    'knowledge_base'
)

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

@require_http_methods(["POST"])
@ensure_csrf_cookie
def generate_and_send_email(request):
    try:
        data = json.loads(request.body)
        transcription = data.get('transcription', '')
        
        if not transcription:
            return JsonResponse({'error': 'Missing transcription'}, status=400)

        email_service = EmailService()
        email_data = email_service.generate_email(transcription)
        success = email_service.send_email(email_data)
        
        if success:
            return JsonResponse({
                'status': 'success',
                'message': 'Email sent successfully',
                'email_data': email_data
            })
        else:
            raise Exception("Failed to send email")
            
    except Exception as e:
        logger.error(f"Error in generate_and_send_email: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

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
        transcription = data.get('transcription', '')
        
        # Initialize HybridRAG with existing knowledge base
        hybrid_rag = HybridRAG()
        
        # Generate insights using RAG
        result = hybrid_rag.generate_insights(transcription)
        
        if 'error' in result:
            logger.error(f"Error in generate_insights: {result['error']}")
            return JsonResponse({'error': result['error']}, status=500)
        
        # Log successful insight generation
        logger.info(f"Generated insights with confidence: {result.get('confidence', 0)}")
        
        return JsonResponse({
            'insights': result.get('insights', ''),
            'confidence': result.get('confidence', 0),
            'sources': result.get('sources', [])
        })
        
    except Exception as e:
        logger.error(f"Error generating insights: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
    
@require_http_methods(["POST"])
@ensure_csrf_cookie
def generate_summary(request):
    try:
        data = json.loads(request.body)
        transcription = data.get('transcription', '')
        
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
        searcher = WebSearcher()
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
