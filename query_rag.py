import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["POSTHOG_DISABLED"] = "1"

from openai import OpenAI
import chromadb

class RAGQueryEngine:
    def __init__(self):
        self.client = OpenAI()
        self.chroma_client = chromadb.PersistentClient(path="./chroma_data")
        self.collection = self.chroma_client.get_collection(name="knowledge_base")

    def query(self, question, n_results=2):
        try:
            # Create embedding for the question
            query_embedding = self.client.embeddings.create(
                input=question,
                model="text-embedding-3-small"
            ).data[0].embedding

            # Query the collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            retrieved_documents = results["documents"][0]

            # Create context from retrieved documents
            context = "\n".join(retrieved_documents)
            
            # Create prompt
            prompt = f"""
            Use the following context to answer the question:
            Context: {context}
            Question: {question}
            Answer:
            """

            # Get response from GPT
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a knowledgeable assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.5
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Error: {str(e)}"

def main():
    # Initialize the RAG query engine
    rag_engine = RAGQueryEngine()
    
    print("RAG Query System Ready (type 'quit' to exit)")
    print("-" * 50)
    
    while True:
        question = input("\nEnter your question: ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
            
        if question:
            answer = rag_engine.query(question)
            print("\nAnswer:", answer)
            print("-" * 50)

if __name__ == "__main__":
    main()