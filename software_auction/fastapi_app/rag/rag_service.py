import logging
from .hybrid_rag import HybridRAG, KNOWLEDGE_BASE_DIR
from django.http import JsonResponse
from ..services.websearch_service import WebSearchService as WebSearcher
import time
import uuid
import os
import json
from django.conf import settings
from pathlib import Path
from typing import Dict, Any, List
from ..services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)

class RAGService:
    """Service class for RAG operations"""

    def __init__(self):
        self.conversation_history = []
        # Use the same knowledge base directory as hybrid_rag
        self.data_dir = KNOWLEDGE_BASE_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"RAG Service using knowledge base directory: {self.data_dir}")

    def add_to_history(self, user_input, bot_response):
        """Add the latest user input and bot response to the conversation history."""
        self.conversation_history.append({"user": user_input, "bot": bot_response})

    def retrieve_information(self, query):
        """Retrieve relevant information based on the query."""
        # Implement your retrieval logic here
        # For example, using a vector store or a database
        retrieved_data = self.perform_retrieval(query)
        return retrieved_data

    def generate_response(self, user_input):
        """Generate a response based on the user input and conversation history."""
        # Retrieve relevant information
        retrieved_data = self.retrieve_information(user_input)

        # Generate a response
        response = self.call_model(retrieved_data)

        # Add to conversation history
        self.add_to_history(user_input, response)

        return response

    def summarize_data(self, data):
        """Summarize the retrieved data to make it concise."""
        # Implement your summarization logic here
        # This could be a simple text summarization or using another model
        return summarized_data

    def call_model(self, summarized_data):
        """Call the language model to generate a response."""
        # Implement your model call here
        return model_response

    @staticmethod
    def handle_enrich_knowledge_base(data: dict) -> dict:
        """Handle knowledge base enrichment request"""
        try:
            rag = HybridRAG()
            
            # Get the knowledge base data directory
            base_dir = KNOWLEDGE_BASE_DIR / 'data'
            base_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize services at the start
            knowledge_service = KnowledgeService()
            web_searcher = WebSearcher()
            
            # Path to text.txt and questions.txt
            text_path = base_dir / 'text.txt'
            questions_path = base_dir / 'questions.txt'
            
            logger.info(f"Looking for text.txt at: {text_path}")
            logger.info(f"Looking for questions.txt at: {questions_path}")
            
            processed_count = 0
            text_summary = ""
            full_content = []
            
            # Process text.txt first
            if os.path.exists(text_path):
                logger.info("Found text.txt file")
                with open(text_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                    full_content.append(text_content)
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
                        model=settings.GPT_MODEL_NAME,
                        messages=[
                            {"role": "system", "content": "You are a precise analyzer that provides clear summaries and identifies document types based on content analysis."},
                            {"role": "user", "content": analysis_prompt}
                        ],
                        temperature=settings.DEFAULT_TEMPERATURE,
                        max_tokens=1000
                    )
                    
                    analysis_result = analysis_response.choices[0].message.content
                    
                    # Split the response into summary and content type
                    summary_section = analysis_result.split("CONTENT TYPE:")[0].replace("SUMMARY:", "").strip()
                    text_summary = summary_section  # Store summary for response
                    content_type_section = analysis_result.split("CONTENT TYPE:")[1].strip()
                    
                    # Add text content to knowledge base with enhanced metadata
                    document = {
                        'content': text_content,
                        'metadata': {
                            'source': 'text.txt',
                            'type': 'base_knowledge',
                            'content_type': content_type_section.split('\n')[0],
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'has_summary': True,
                            'summary': summary_section
                        }
                    }
                    
                    # Add to knowledge base
                    rag.add_to_knowledge_base(document)
                    processed_count += 1
                    logger.info("Successfully added text.txt to knowledge base with summary and content type analysis")
                    
                except Exception as e:
                    logger.error(f"Error analyzing text content: {str(e)}")
                    return {
                        'status': 'error',
                        'message': f'Error analyzing text content: {str(e)}'
                    }
            
            # Process questions.txt and their answers
            if os.path.exists(questions_path):
                logger.info("Found questions.txt file")
                with open(questions_path, 'r', encoding='utf-8') as f:
                    questions = f.readlines()
                    logger.info(f"Read {len(questions)} questions from questions.txt")
                
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
                            model=settings.GPT_MODEL_NAME,
                            messages=[
                                {"role": "system", "content": "Generate a comprehensive answer based on search results."},
                                {"role": "user", "content": answer_prompt}
                            ],
                            temperature=settings.DEFAULT_TEMPERATURE,
                            max_tokens=settings.DEFAULT_MAX_TOKENS
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
                            model=settings.GPT_MODEL_NAME,
                            messages=[
                                {"role": "system", "content": "You are a precise analyzer that provides clear summaries and identifies content types."},
                                {"role": "user", "content": answer_analysis_prompt}
                            ],
                            temperature=settings.DEFAULT_TEMPERATURE,
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
                            model=settings.EMBEDDING_MODEL_NAME
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
            return {
                'status': 'success',
                'message': f'Knowledge base enriched successfully with {processed_count} documents',
                'text_summary': text_summary if text_summary else "No text.txt summary available",
                'full_content': '\n\n'.join(full_content)
            }
            
        except Exception as e:
            logger.error(f"Error enriching knowledge base: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

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

    async def save_document(self, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Save a document to the knowledge base"""
        try:
            # Generate unique filename
            timestamp = int(time.time())
            file_path = self.data_dir / f"rag_service_{timestamp}.txt"
            
            # Save document
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Saved document to {file_path}")
            
            return {
                'status': 'success',
                'file_path': str(file_path),
                'metadata': metadata or {}
            }
            
        except Exception as e:
            logger.error(f"Error saving document: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def load_documents(self) -> List[Dict[str, Any]]:
        """Load all documents from the knowledge base"""
        try:
            documents = []
            for file_path in self.data_dir.glob('*.txt'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            documents.append({
                                'content': content,
                                'file_path': str(file_path),
                                'metadata': {
                                    'source': str(file_path),
                                    'timestamp': file_path.stat().st_mtime,
                                    'type': 'rag_service'
                                }
                            })
                except Exception as e:
                    logger.error(f"Error loading document {file_path}: {e}")
            
            return documents
            
        except Exception as e:
            logger.error(f"Error loading documents: {e}")
            return []

    async def delete_document(self, file_path: str) -> Dict[str, Any]:
        """Delete a document from the knowledge base"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"Deleted document {file_path}")
                return {
                    'status': 'success',
                    'message': f'Document {file_path} deleted'
                }
            else:
                return {
                    'status': 'error',
                    'error': f'Document {file_path} not found'
                }
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    @staticmethod
    def handle_text_query(query: str) -> str:
        """Handle text mode query using only knowledge base"""
        try:
            logger.info(f"Processing text query: {query}")
            
            rag = HybridRAG()
            
            # Get context from knowledge base
            context = rag.get_factual_context(query)
            
            # Format context as a string if it's not already
            if isinstance(context, (list, dict)):
                context = str(context)
            
            # Generate response using only knowledge base context
            response = rag.generate_response(query, context=context)
            
            if not response:
                raise ValueError("No response generated from RAG service")
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing text query: {str(e)}")
            raise Exception(f"Failed to process query: {str(e)}") 