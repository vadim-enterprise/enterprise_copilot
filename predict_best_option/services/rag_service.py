import logging
from ..hybrid_rag import HybridRAG
from django.http import JsonResponse
from ..web_search import WebSearcher
import time
import uuid
import os
import json
from ..settings import GPT_MODEL_NAME, EMBEDDING_MODEL_NAME, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS

logger = logging.getLogger(__name__)

class RAGService:
    """Service class for RAG operations"""

    @staticmethod
    def handle_enrich_knowledge_base(request) -> JsonResponse:
        """Handle knowledge base enrichment request"""
        try:
            rag = HybridRAG()
            
            # Get the base directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Path to text.txt and questions.txt
            text_path = os.path.join(base_dir, 'data', 'text.txt')
            questions_path = os.path.join(base_dir, 'data', 'questions.txt')
            
            logger.info(f"Looking for text.txt at: {text_path}")
            logger.info(f"Looking for questions.txt at: {questions_path}")
            
            processed_count = 0
            
            # Process text.txt first
            if os.path.exists(text_path):
                logger.info("Found text.txt file")
                with open(text_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                    logger.info(f"Read {len(text_content)} characters from text.txt")
                    
                # Generate summary and content type analysis
                analysis_prompt = f"""
                Analyze the following text and provide:
                1. A comprehensive summary of up to 500 words that captures the main points, key findings, and important details.
                2. A description of the content type (e.g., scientific paper, newspaper article, technical documentation, etc.) 
                    with explanation of why you classified it as such based on its structure, style, and content.

                Text:
                {text_content}

                Format your response as:
                SUMMARY:
                [Your summary here]

                CONTENT TYPE:
                [Content type and explanation here]
                """
                
                try:
                    analysis_response = rag.openai_client.chat.completions.create(
                        model=GPT_MODEL_NAME,
                        messages=[
                            {"role": "system", "content": "You are a precise analyzer that provides clear summaries and identifies document types based on content analysis."},
                            {"role": "user", "content": analysis_prompt}
                        ],
                        temperature=DEFAULT_TEMPERATURE,
                        max_tokens=1000
                    )
                    
                    analysis_result = analysis_response.choices[0].message.content
                    
                    # Split the response into summary and content type
                    summary_section = analysis_result.split("CONTENT TYPE:")[0].replace("SUMMARY:", "").strip()
                    content_type_section = analysis_result.split("CONTENT TYPE:")[1].strip()
                    
                    # Add text content to knowledge base with enhanced metadata
                    document = {
                        'content': f"""
                        ORIGINAL TEXT SUMMARY:
                        {summary_section}
                        
                        CONTENT TYPE ANALYSIS:
                        {content_type_section}
                        """.strip(),
                        'metadata': {
                            'source': 'text.txt',
                            'type': 'base_knowledge',
                            'content_type': content_type_section.split('\n')[0],  # First line of content type section
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'has_summary': True,
                            'summary_length': len(summary_section.split())
                        }
                    }
                    
                    # Generate embedding and add to ChromaDB
                    embedding = rag.openai_client.embeddings.create(
                        input=document['content'],
                        model=EMBEDDING_MODEL_NAME
                    ).data[0].embedding
                    
                    doc_id = str(uuid.uuid4())
                    rag.collection.add(
                        documents=[document['content']],
                        embeddings=[embedding],
                        metadatas=[document['metadata']],
                        ids=[doc_id]
                    )
                    processed_count += 1
                    logger.info("Successfully added text.txt to knowledge base with summary and content type analysis")
                    
                except Exception as e:
                    logger.error(f"Error analyzing text content: {str(e)}")
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Error analyzing text content: {str(e)}'
                    })
            
            # Process questions.txt and their answers
            if os.path.exists(questions_path):
                logger.info("Found questions.txt file")
                with open(questions_path, 'r', encoding='utf-8') as f:
                    questions = f.readlines()
                    logger.info(f"Read {len(questions)} questions from questions.txt")
                
                # Initialize knowledge service for processing search results
                from ..services.knowledge_service import KnowledgeService
                knowledge_service = KnowledgeService()
                web_searcher = WebSearcher()
                
                for question in questions:
                    question = question.strip()
                    if question:
                        logger.info(f"Processing question: {question}")
                        
                        # Get search results
                        search_results = web_searcher.search_and_process(question, filter_context=True)
                        logger.info(f"Found {len(search_results)} results for question: {question}")
                        
                        # Process and add search results to knowledge base
                        if search_results:
                            enriched_results = knowledge_service.enrich_from_search_results(search_results, question)
                            processed_count += len([r for r in enriched_results if r.get('added_to_kb')])
                            logger.info(f"Added {len(enriched_results)} answers for question: {question}")
                        
                        # Generate a comprehensive answer using the search results
                        answer_prompt = f"""
                        Based on the search results, provide a comprehensive answer to this question:
                        Question: {question}
                        
                        Search Results:
                        {json.dumps(search_results, indent=2)}
                        
                        Provide a detailed, factual answer that synthesizes the information.
                        """
                        
                        answer_response = rag.openai_client.chat.completions.create(
                            model=GPT_MODEL_NAME,
                            messages=[
                                {"role": "system", "content": "Generate a comprehensive answer based on search results."},
                                {"role": "user", "content": answer_prompt}
                            ],
                            temperature=DEFAULT_TEMPERATURE,
                            max_tokens=DEFAULT_MAX_TOKENS
                        )
                        
                        answer = answer_response.choices[0].message.content
                        
                        # After generating the answer, add analysis
                        answer_analysis_prompt = f"""
                        Analyze the following answer and provide:
                        1. A comprehensive summary of up to 500 words that captures the main points and key findings.
                        2. A description of the content type and nature of this answer (e.g., technical explanation, factual description, analysis, etc.)
                            with explanation of why you classified it as such based on its structure and content.

                        Answer Text:
                        {answer}

                        Format your response as:
                        SUMMARY:
                        [Your summary here]

                        CONTENT TYPE:
                        [Content type and explanation here]
                        """

                        answer_analysis_response = rag.openai_client.chat.completions.create(
                            model=GPT_MODEL_NAME,
                            messages=[
                                {"role": "system", "content": "You are a precise analyzer that provides clear summaries and identifies content types."},
                                {"role": "user", "content": answer_analysis_prompt}
                            ],
                            temperature=DEFAULT_TEMPERATURE,
                            max_tokens=1000
                        )

                        analysis_result = answer_analysis_response.choices[0].message.content
                        summary_section = analysis_result.split("CONTENT TYPE:")[0].replace("SUMMARY:", "").strip()
                        content_type_section = analysis_result.split("CONTENT TYPE:")[1].strip()

                        # Create the answer document with analysis
                        answer_document = {
                            'content': f"""
                            Question: {question}
                            
                            ANSWER SUMMARY:
                            {summary_section}
                            
                            CONTENT TYPE ANALYSIS:
                            {content_type_section}
                            """.strip(),
                            'metadata': {
                                'source': 'questions.txt',
                                'type': 'synthesized_answer',
                                'question': question,
                                'content_type': content_type_section.split('\n')[0],
                                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                                'has_summary': True,
                                'summary_length': len(summary_section.split())
                            }
                        }
                        
                        # Generate embedding for answer
                        answer_embedding = rag.openai_client.embeddings.create(
                            input=answer_document['content'],
                            model=EMBEDDING_MODEL_NAME
                        ).data[0].embedding
                        
                        # Add answer to ChromaDB
                        answer_id = str(uuid.uuid4())
                        rag.collection.add(
                            documents=[answer_document['content']],
                            embeddings=[answer_embedding],
                            metadatas=[answer_document['metadata']],
                            ids=[answer_id]
                        )
                        processed_count += 1
                        logger.info(f"Added synthesized answer for question: {question}")
            
            logger.info(f"Enrichment complete. Processed {processed_count} documents total.")
            return JsonResponse({
                'status': 'success',
                'message': f'Knowledge base enriched successfully with {processed_count} documents'
            })
            
        except Exception as e:
            logger.error(f"Error enriching knowledge base: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })

    @staticmethod
    def handle_inspect_knowledge_base(request) -> JsonResponse:
        """Handle knowledge base inspection request"""
        try:
            rag = HybridRAG()
            result = rag.inspect_collection()
            
            logger.info(f"Inspection result: {result}")
            
            return JsonResponse({
                'status': 'success',
                'documents': result.get('documents', []),
                'count': result.get('count', 0)
            })
            
        except Exception as e:
            logger.error(f"Error inspecting knowledge base: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e),
                'documents': [],
                'count': 0
            })

    @staticmethod
    def handle_clear_knowledge_base(request) -> JsonResponse:
        """Handle knowledge base clearing request"""
        try:
            rag = HybridRAG()
            success = rag.clear_knowledge_base()
            
            return JsonResponse({
                'status': 'success' if success else 'error',
                'message': 'Knowledge base cleared successfully' if success else 'Failed to clear knowledge base'
            })
            
        except Exception as e:
            logger.error(f"Error clearing knowledge base: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }) 