from typing import Dict, Any
import logging
from django.conf import settings
from software_auction.fastapi_app.rag.hybrid_rag import HybridRAG

logger = logging.getLogger(__name__)

class AnalysisService:
    def __init__(self):
        self.rag = HybridRAG()
        
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze text using RAG-enhanced analysis"""
        try:
            # Get insights using RAG
            insights = self.rag.generate_insights(text)
            
            # Generate summary
            summary = self.rag.generate_summary(text)
                        
            return {
                'insights': insights,
                'summary': summary,
            }
            
        except Exception as e:
            logger.error(f"Error in text analysis: {str(e)}")
            return {'error': str(e)}
            
    def query_knowledge_base(self, question: str, style: str = "conversation", user_context: Dict = None) -> Dict[str, Any]:
        """Query the knowledge base"""
        try:
            return self.rag.query(question, style, user_context)
        except Exception as e:
            logger.error(f"Error querying knowledge base: {str(e)}")
            return {'error': str(e)}
            
    def add_to_knowledge_base(self, document: Dict[str, Any]) -> bool:
        """Add document to knowledge base"""
        try:
            return self.rag.add_to_knowledge_base(document)
        except Exception as e:
            logger.error(f"Error adding to knowledge base: {str(e)}")
            return False
            
    def clear_knowledge_base(self) -> bool:
        """Clear knowledge base"""
        try:
            return self.rag.clear_knowledge_base()
        except Exception as e:
            logger.error(f"Error clearing knowledge base: {str(e)}")
            return False
            
    def inspect_knowledge_base(self) -> Dict[str, Any]:
        """Inspect knowledge base"""
        try:
            return self.rag.inspect_collection()
        except Exception as e:
            logger.error(f"Error inspecting knowledge base: {str(e)}")
            return {'error': str(e)} 