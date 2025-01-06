import logging
import time
import uuid
from typing import Dict, List
from openai import OpenAI
import os
from ..settings import GPT_MODEL_NAME, EMBEDDING_MODEL_NAME, DEFAULT_TEMPERATURE

logger = logging.getLogger(__name__)

class KnowledgeService:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
    def enrich_from_search_results(self, search_results: List[Dict], query: str) -> List[Dict]:
        """Process search results and add to knowledge base"""
        try:
            from ..hybrid_rag import HybridRAG
            rag = HybridRAG()
            
            enriched_results = []
            for result in search_results:
                try:
                    # Generate enhanced summary
                    enhanced_summary = self._generate_enhanced_summary(result)
                    result['enhanced_summary'] = enhanced_summary
                    
                    # Create and add document to knowledge base
                    document = self._create_document(result, enhanced_summary, query)
                    success = self._add_to_knowledge_base(document, rag)
                    
                    result['added_to_kb'] = success
                    enriched_results.append(result)
                    
                except Exception as e:
                    logger.error(f"Error processing result {result.get('title')}: {str(e)}")
                    continue
                    
            return enriched_results
            
        except Exception as e:
            logger.error(f"Error enriching from search results: {str(e)}")
            return []
            
    def _generate_enhanced_summary(self, result: Dict) -> Dict:
        """Generate enhanced summary and content type analysis using OpenAI"""
        analysis_prompt = f"""
        Analyze the following web content and provide:
        1. A comprehensive summary of up to 500 words that captures the main points, key findings, and important details.
        2. A description of the content type (e.g., blog post, news article, academic paper, documentation, forum discussion, etc.) 
           with explanation of why you classified it as such based on its structure, style, and content.

        Title: {result['title']}
        Content: {result['summary']}
        URL: {result['url']}

        Format your response as:
        SUMMARY:
        [Your summary here]

        CONTENT TYPE:
        [Content type and explanation here]
        """
        
        response = self.openai_client.chat.completions.create(
            model=GPT_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a precise analyzer that provides clear summaries and identifies document types based on content analysis."},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=1000
        )
        
        analysis_result = response.choices[0].message.content
        
        # Split the response into summary and content type
        summary_section = analysis_result.split("CONTENT TYPE:")[0].replace("SUMMARY:", "").strip()
        content_type_section = analysis_result.split("CONTENT TYPE:")[1].strip()
        
        return {
            'summary': summary_section,
            'content_type': content_type_section
        }
        
    def _create_document(self, result: Dict, enhanced_analysis: Dict, query: str) -> Dict:
        """Create document for knowledge base"""
        return {
            'content': f"""
            Title: {result['title']}
            Source URL: {result['url']}
            
            SUMMARY:
            {enhanced_analysis['summary']}
            
            CONTENT TYPE ANALYSIS:
            {enhanced_analysis['content_type']}
            """.strip(),
            'metadata': {
                'source': result['url'],
                'title': result['title'],
                'timestamp': result['timestamp'],
                'type': 'web_search',
                'query': query,
                'content_type': enhanced_analysis['content_type'].split('\n')[0],  # First line of content type
                'search_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'has_summary': True,
                'summary_length': len(enhanced_analysis['summary'].split())
            }
        }
        
    def _add_to_knowledge_base(self, document: Dict, rag) -> bool:
        """Add document to knowledge base"""
        try:
            # Generate embedding
            embedding = self.openai_client.embeddings.create(
                input=document['content'],
                model=EMBEDDING_MODEL_NAME
            ).data[0].embedding
            
            # Add to ChromaDB
            doc_id = str(uuid.uuid4())
            rag.collection.add(
                documents=[document['content']],
                embeddings=[embedding],
                metadatas=[document['metadata']],
                ids=[doc_id]
            )
            
            logger.info(f"Added document to knowledge base: {document['metadata']['title']}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding to knowledge base: {str(e)}")
            return False 