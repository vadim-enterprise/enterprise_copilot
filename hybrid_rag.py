import os
from typing import Dict, Any, List
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["POSTHOG_DISABLED"] = "1"

from openai import OpenAI
import chromadb

class HybridRAG:
    def __init__(self):
        self.client = OpenAI()
        self.chroma_client = chromadb.PersistentClient(path="./chroma_data")
        self.collection = self.chroma_client.get_collection(name="knowledge_base")
        self.last_query_metadata = {}  # Store metadata about last query
        
        # Initialize prompt templates
        self.prompt_templates = self.load_prompt_templates()

    def load_prompt_templates(self) -> Dict[str, str]:
        """Load different prompt templates for various styles"""
        return {
            "default": """
                Provide a clear and engaging response that:
                - Uses facts accurately
                - Maintains clarity
                - Includes relevant examples
            """,
            "storytelling": """
                Present this information as an engaging story that:
                - Has a clear narrative arc
                - Uses metaphors and analogies
                - Connects emotionally while maintaining accuracy
            """,
            "tutorial": """
                Create a step-by-step tutorial that:
                - Breaks down complex concepts
                - Provides practical examples
                - Includes actionable steps
            """,
            "conversation": """
                Present this as a friendly dialogue that:
                - Uses natural, conversational language
                - Anticipates and addresses questions
                - Maintains an engaging back-and-forth flow
            """,
            "analytical": """
                Analyze this information critically by:
                - Examining key components
                - Providing detailed analysis
                - Drawing meaningful conclusions
            """
        }

    def get_factual_context(self, query: str, n_results: int = 2) -> Dict[str, Any]:
        """Enhanced RAG component with metadata tracking"""
        query_embedding = self.client.embeddings.create(
            input=query,
            model="text-embedding-3-small"
        ).data[0].embedding

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include_metadata=True
        )

        # Store metadata for tracking
        self.last_query_metadata = {
            "documents": results["documents"][0],
            "metadata": results["metadatas"][0],
            "distances": results["distances"][0]
        }

        return results["documents"][0]

    def creative_response(self, facts: List[str], query: str, style: str = "default", 
                         user_context: Dict[str, Any] = None) -> str:
        """Enhanced Prompt Engineering component with user context"""
        style_prompt = self.prompt_templates.get(style, self.prompt_templates["default"])
        
        # Include user context if available
        context_prompt = ""
        if user_context:
            context_prompt = f"""
            Consider this user context:
            - Technical level: {user_context.get('technical_level', 'general')}
            - Preferred detail: {user_context.get('detail_preference', 'balanced')}
            - Prior knowledge: {user_context.get('prior_knowledge', 'none')}
            """

        prompt = f"""
        Using these verified facts:
        {facts}

        {context_prompt}

        Following this style: {style_prompt}

        Answer this question: {query}

        Requirements:
        - Use the facts accurately
        - Be creative in presentation
        - Maintain engaging tone
        - Add relevant examples
        - Make it memorable
        - Adapt to user's technical level
        """

        response = self.client.chat.completions.create(
            model="gpt-4",  # Using GPT-4 for better response quality
            messages=[
                {"role": "system", "content": "You are an expert at combining factual accuracy with creative presentation."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=self.get_temperature(style)
        )

        return response.choices[0].message.content

    def get_temperature(self, style: str) -> float:
        """Determine appropriate temperature based on style"""
        temperature_map = {
            "default": 0.7,
            "storytelling": 0.8,
            "tutorial": 0.5,
            "conversation": 0.7,
            "analytical": 0.3
        }
        return temperature_map.get(style, 0.7)

    def query(self, question: str, style: str = "default", 
              user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Enhanced query method with metadata and error handling"""
        try:
            # 1. Get factual context (RAG)
            facts = self.get_factual_context(question)
            
            # 2. Generate creative response (Prompt Engineering)
            answer = self.creative_response(facts, question, style, user_context)
            
            # 3. Return response with metadata
            return {
                "answer": answer,
                "confidence": 1 - min(self.last_query_metadata.get("distances", [0])),
                "style_used": style,
                "sources": self.last_query_metadata.get("metadata", [])
            }

        except Exception as e:
            return {
                "error": str(e),
                "answer": "An error occurred while processing your query.",
                "confidence": 0.0,
                "style_used": style
            }

def main():
    # Initialize the hybrid system
    hybrid_system = HybridRAG()
    
    print("Enhanced Hybrid RAG System Ready!")
    print("Available styles: default, storytelling, tutorial, conversation, analytical")
    print("-" * 50)
    
    # Example user context
    user_context = {
        "technical_level": "intermediate",
        "detail_preference": "detailed",
        "prior_knowledge": "some"
    }
    
    while True:
        question = input("\nEnter your question (or 'quit' to exit): ").strip()
        if question.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
            
        style = input("Enter style (or press Enter for default): ").strip().lower()
        if not style:
            style = "default"
            
        if question:
            result = hybrid_system.query(question, style, user_context)
            
            print("\nAnswer:", result["answer"])
            print(f"Confidence: {result['confidence']:.2f}")
            print(f"Style Used: {result['style_used']}")
            if result.get("sources"):
                print("Sources:", result["sources"])
            print("-" * 50)

if __name__ == "__main__":
    main()