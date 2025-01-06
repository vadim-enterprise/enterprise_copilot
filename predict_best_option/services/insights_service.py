import logging
from ..hybrid_rag import HybridRAG

logger = logging.getLogger(__name__)

class InsightsService:
    def __init__(self):
        self.rag = HybridRAG()

    def generate_insights(self, transcription: str) -> dict:
        """Generate insights from transcription using RAG"""
        try:
            return self.rag.generate_insights(transcription)
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            raise

    def generate_summary(self, transcription: str) -> dict:
        """Generate summary from transcription using RAG"""
        try:
            return self.rag.generate_summary(transcription)
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            raise 