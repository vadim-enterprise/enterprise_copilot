import os
from typing import Dict, List, Any
import logging
from openai import OpenAI
import chromadb
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import json
import time
import uuid
from .web_search import WebSearcher
from .settings import GPT_MODEL_NAME, EMBEDDING_MODEL_NAME, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS

logger = logging.getLogger(__name__)
MODEL_CHOICE = "openai"

class HybridRAG:
    def __init__(self, model_choice = MODEL_CHOICE):
        """Initialize RAG with ChromaDB and chosen model"""
        try:
            # Set up paths
            self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.knowledge_base_dir = os.path.join(self.base_dir, 'knowledge_base')
            self.questions_file = os.path.join(self.knowledge_base_dir, 'questions.txt')
            
            # Store model choice
            self.model_choice = model_choice
            
            # Create necessary directories
            os.makedirs(self.knowledge_base_dir, exist_ok=True)
            
            # Initialize ChromaDB
            self.chroma_dir = os.path.join(self.base_dir, 'chroma_db')
            os.makedirs(self.chroma_dir, exist_ok=True)
            
            # Initialize ChromaDB client and collection
            try:
                self.chroma_client = chromadb.PersistentClient(path=self.chroma_dir)
                logger.info("Successfully initialized ChromaDB client")
                self._initialize_empty_collection(reset=False)  # Don't reset by default
            except Exception as e:
                logger.error(f"Error initializing ChromaDB: {str(e)}")
                raise
            
            # Initialize last query metadata
            self.last_query_metadata = {
                "distances": [1.0],
                "metadata": [],
                "documents": [""]
            }
            
            # Initialize model
            try:
                self._initialize_model()
                self.web_searcher = WebSearcher(model_choice=self.model_choice)
            except Exception as e:
                logger.error(f"Error in initialization: {str(e)}")
                raise
            
        except Exception as e:
            logger.error(f"Error initializing HybridRAG: {str(e)}")
            raise

    def _initialize_model(self):
        """Initialize the chosen model"""
        if self.model_choice == "openai":
            if not os.getenv('OPENAI_API_KEY'):
                raise ValueError("OpenAI API key not found in environment variables")
            self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            # Don't initialize Llama models in OpenAI mode
            self.llama_model = None
            self.llama_tokenizer = None
        else:
            try:
                self.openai_client = None
                model_name = "meta-llama/Llama-2-7b-chat-hf"
                # Add SSL verification disable option for development
                os.environ['CURL_CA_BUNDLE'] = ''  # Temporarily disable SSL verification
                self.llama_tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.llama_model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    torch_dtype=torch.float16,
                    device_map="auto"
                )
            except Exception as e:
                logger.error(f"Failed to initialize Llama model: {str(e)}")
                logger.warning("Falling back to OpenAI")
                self.model_choice = "openai"
                self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                self.llama_model = None
                self.llama_tokenizer = None

    def _initialize_empty_collection(self, reset=False):
        """Initialize ChromaDB collection"""
        try:
            try:
                # Try to get existing collection
                self.collection = self.chroma_client.get_collection(name="knowledge_base")
                if reset:
                    # Only delete if reset is requested
                    self.chroma_client.delete_collection(name="knowledge_base")
                    logger.info("Deleted existing knowledge base collection")
                    # Create new empty collection
                    self.collection = self.chroma_client.create_collection(
                        name="knowledge_base",
                        metadata={"hnsw:space": "cosine"}
                    )
                    logger.info("Created new empty knowledge base collection")
                else:
                    logger.info("Retrieved existing knowledge base collection")
            except Exception as e:
                logger.info("Collection does not exist, creating new one")
                # Create new empty collection
                self.collection = self.chroma_client.create_collection(
                    name="knowledge_base",
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info("Created new empty knowledge base collection")
            
        except Exception as e:
            logger.error(f"Error in _initialize_empty_collection: {str(e)}")
            raise

    def is_enriched(self):
        """Check if knowledge base has content"""
        try:
            # Check if collection has any documents
            all_docs = self.collection.get()
            
            # Debug print to verify content
            logger.info(f"Checking enrichment status:")
            logger.info(f"Total documents: {len(all_docs.get('documents', []))}")
            
            # Consider enriched if there are any documents
            return len(all_docs.get('documents', [])) > 0
        except Exception as e:
            logger.error(f"Error checking enrichment status: {str(e)}")
            return False

    def get_factual_context(self, query: str) -> str:
        """Get relevant context from knowledge base"""
        try:
            # Initialize collection if needed
            _ = self.collection
            
            # Check for documents directly
            all_docs = self.collection.get()
            if not all_docs['documents']:
                return "Knowledge base not enriched. Please click 'Enrich Knowledge Base' first."
            
            # Generate embedding for the query
            query_embedding = self.openai_client.embeddings.create(
                input=query,
                model="text-embedding-ada-002"
            ).data[0].embedding
            
            # Search ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=5,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Update last query metadata
            self.last_query_metadata = {
                "distances": results.get("distances", [1.0])[0],
                "metadata": results.get("metadatas", [{}])[0],
                "documents": results.get("documents", [""])[0]
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting factual context: {str(e)}")
            # Reset metadata on error
            self.last_query_metadata = {
                "distances": [1.0],
                "metadata": [],
                "documents": [""]
            }
            return "Error retrieving context from knowledge base"

    def ingest_documents(self, directory_path: str) -> Dict[str, Any]:
        """
        Ingest text documents from a directory for RAG training
        """
        try:
            directory = Path(directory_path)
            processed_files = 0
            failed_files = 0
            
            print(f"Processing documents from {directory_path}...")
            
            for file_path in directory.glob('*.txt'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        
                        # Split content into chunks (simple splitting - could be more sophisticated)
                        chunks = self._chunk_text(content, chunk_size=500)
                        
                        # Generate embeddings for each chunk
                        for chunk in chunks:
                            embedding = self.openai_client.embeddings.create(
                                input=chunk,
                                model="text-embedding-ada-002"
                            ).data[0].embedding
                            
                            # Create unique ID for chunk
                            chunk_id = hashlib.md5(chunk.encode()).hexdigest()
                            
                            # Store in ChromaDB with metadata
                            self.collection.add(
                                documents=[chunk],
                                embeddings=[embedding],
                                ids=[chunk_id],
                                metadatas=[{
                                    'source': str(file_path),
                                    'timestamp': time.time(),
                                    'chunk_size': len(chunk)
                                }]
                            )
                        
                        processed_files += 1
                        print(f"Processed {file_path.name}")
                        
                except Exception as e:
                    print(f"Error processing {file_path}: {str(e)}")
                    failed_files += 1
                    
            return {
                'status': 'success',
                'processed_files': processed_files,
                'failed_files': failed_files
            }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def generate_insights(self, transcription: str) -> Dict[str, Any]:
        """Generate insights using RAG-enhanced prompting"""
        try:
            # Get relevant context from RAG
            context = self.get_factual_context(transcription)
            
            # Enhanced prompt with specific bullet point formatting
            prompt = f"""
            Based on our knowledge base context and analyzing this conversation, generate insights in exactly this format:

            • KEY INSIGHTS:
            - [First key insight with complete sentence]
            - [Second key insight with complete sentence]
            - [Third key insight if applicable]

            • KNOWLEDGE BASE CONNECTIONS:
            - [First connection to existing knowledge]
            - [Second connection if applicable]

            • RECOMMENDATIONS:
            - [First actionable recommendation]
            - [Second recommendation if applicable]

            Keep each bullet point as a complete sentence and ensure total response is under 150 words.
            Start each bullet with a dash (-) and each section with a bullet point (•).

            Context: {context}
            Conversation: {transcription}
            """
            
            response = self.openai_client.chat.completions.create(
                model=GPT_MODEL_NAME,
                messages=[
                    {"role": "system", "content": """
                        You are a concise analyst. Format your response with:
                        • Main sections marked with bullet points (•)
                        - Sub-points marked with dashes (-)
                        Keep each point as a complete sentence.
                        Never use other bullet styles or numbering.
                    """},
                    {"role": "user", "content": prompt}
                ],
                temperature=DEFAULT_TEMPERATURE,
                max_tokens=DEFAULT_MAX_TOKENS
            )
            
            insights = response.choices[0].message.content
            
            # Calculate confidence based on context relevance
            confidence = 1 - min(self.last_query_metadata.get("distances", [0]))
            
            return {
                'insights': insights,
                'confidence': confidence,
                'sources': [
                    {
                        'source': meta.get('source', '')[:100],
                        'relevance': 1 - dist,
                        'timestamp': meta.get('timestamp', '')
                    }
                    for meta, dist in zip(
                        self.last_query_metadata.get("metadata", [])[:2],
                        self.last_query_metadata.get("distances", [])[:2]
                    )
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in generate_insights: {str(e)}")
            return {'error': str(e)}
    
    def generate_summary(self, transcription: str) -> Dict[str, Any]:
        """Generate summary using RAG-enhanced prompting"""
        try:
            # Get context with temporal awareness
            context = self.get_factual_context(transcription)
            
            # Enhanced prompt with RAG integration
            prompt = f"""
            Using our knowledge base context:
            {context}

            Provide a comprehensive summary of this conversation:
            {transcription}

            Structure the summary as follows:

            CONTEXT ALIGNMENT:
            - How this discussion relates to existing documentation
            - Any updates to previous decisions or policies
            - Relevant historical context from our knowledge base

            MAIN POINTS:
            - Key topics discussed
            - Decisions made
            - Changes from previous positions

            NEXT STEPS:
            - Action items with owners
            - Timeline commitments
            - Required follow-ups

            KNOWLEDGE BASE UPDATES:
            - Suggest specific updates needed
            - Identify gaps in current documentation
            - Note any policy or procedure changes

            Use specific references to our knowledge base where relevant.
            """
            
            response = self.openai_client.chat.completions.create(
                model=GPT_MODEL_NAME,
                messages=[
                    {"role": "system", "content": """
                        You are an expert at synthesizing conversations and connecting them to organizational knowledge.
                        Focus on continuity with existing documentation and clear next steps.
                        Highlight any contradictions or updates needed in the knowledge base.
                    """},
                    {"role": "user", "content": prompt}
                ],
                temperature=DEFAULT_TEMPERATURE,
                max_tokens=DEFAULT_MAX_TOKENS
            )
            
            # Enhanced metadata handling
            confidence = 1 - min(self.last_query_metadata.get("distances", [0]))
            sources = [
                {
                    'source': meta.get('source', ''),
                    'relevance': 1 - dist,
                    'timestamp': meta.get('timestamp', ''),
                    'context_snippet': doc[:100] + "..." if len(doc) > 100 else doc
                }
                for meta, dist, doc in zip(
                    self.last_query_metadata.get("metadata", []),
                    self.last_query_metadata.get("distances", []),
                    self.last_query_metadata.get("documents", [])
                )
            ]
            
            return {
                'summary': response.choices[0].message.content,
                'confidence': confidence,
                'sources': sources,
                'context_used': context[:200] + "..." if len(context) > 200 else context,
                'suggested_updates': self._identify_knowledge_gaps(transcription, context)
            }
            
        except Exception as e:
            return {'error': str(e)}
        
    def _identify_knowledge_gaps(self, transcription: str, context: str) -> List[Dict[str, Any]]:
        """Helper method to identify potential knowledge base updates needed"""
        try:
            prompt = f"""
            Compare this conversation:
            {transcription}

            With our existing knowledge:
            {context}

            Identify specific gaps or updates needed in our knowledge base.
            Format as JSON array with 'topic', 'current_state', and 'suggested_update' fields.
            """
            
            response = self.openai_client.chat.completions.create(
                model=GPT_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "Identify knowledge base gaps and needed updates."},
                    {"role": "user", "content": prompt}
                ],
                temperature=DEFAULT_TEMPERATURE
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            print(f"Error identifying knowledge gaps: {str(e)}")
            return []

    def generate_email(self, transcription: str) -> Dict[str, Any]:
        """Generate email using RAG-enhanced prompting"""
        try:
            context = self.get_factual_context(transcription)
            
            prompt = f"""
            Using relevant context from our knowledge base:
            {context}
            
            And based on this conversation:
            {transcription}
            
            Generate a professional email that:
            1. Summarizes key points
            2. Includes relevant background information
            3. Outlines next steps
            4. Maintains appropriate tone and context
            
            Format as JSON with "to", "subject", and "body" fields.
            """
            
            response = self.openai_client.chat.completions.create(
                model=GPT_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are an expert at writing professional emails based on conversations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=DEFAULT_TEMPERATURE
            )
            
            return {
                'email_data': json.loads(response.choices[0].message.content),
                'confidence': 1 - min(self.last_query_metadata.get("distances", [0])),
                'sources': self.last_query_metadata.get("metadata", [])
            }
            
        except Exception as e:
            return {'error': str(e)}

    def query(self, question: str, style: str = "conversation", user_context: Dict = None) -> Dict[str, Any]:
        """Query method for real-time conversation"""
        if not self.is_enriched:
            return {
                'answer': "Knowledge base not enriched. Please click 'Enrich Knowledge Base' first.",
                'confidence': 0.0,
                'style_used': style,
                'sources': [],
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        try:
            # Get context from knowledge base only
            context = self.get_factual_context(question)
            
            # Enhanced prompt using only RAG context
            prompt = f"""
            Using our knowledge base context:
            
            {context}
            
            Question: {question}
            
            Provide a comprehensive answer that:
            1. Uses our existing knowledge base
            2. Indicates confidence in the information
            3. Notes if additional research might be needed
            
            User Context: {json.dumps(user_context) if user_context else 'None'}
            Style: {style}
            """
            
            response = self.openai_client.chat.completions.create(
                model=GPT_MODEL_NAME,
                messages=[
                    {"role": "system", "content": """
                        You are an expert at providing information from our knowledge base.
                        Be clear about what you know and what might need additional research.
                    """},
                    {"role": "user", "content": prompt}
                ],
                temperature=DEFAULT_TEMPERATURE,
                max_tokens=DEFAULT_MAX_TOKENS
            )
            
            return {
                'answer': response.choices[0].message.content,
                'confidence': 1 - min(self.last_query_metadata.get("distances", [1.0])),
                'style_used': style,
                'sources': [s['source'] for s in self.last_query_metadata.get("metadata", [])],
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'answer': "Error processing query",
                'confidence': 0.0
            }

    def inspect_collection(self) -> Dict[str, Any]:
        """Get knowledge base contents"""
        try:
            # Get all documents from collection
            all_docs = self.collection.get()
            
            # Format the results
            documents = []
            if all_docs and 'documents' in all_docs:
                for i, doc in enumerate(all_docs['documents']):
                    metadata = all_docs.get('metadatas', [{}])[i] if 'metadatas' in all_docs else {}
                    doc_id = all_docs.get('ids', [])[i] if 'ids' in all_docs else f"doc_{i}"
                    
                    documents.append({
                        'id': doc_id,
                        'content': doc,
                        'metadata': metadata
                    })
            
            return {
                'status': 'success',
                'documents': documents,
                'count': len(documents)
            }
            
        except Exception as e:
            logger.error(f"Error inspecting collection: {str(e)}")
            return {
                'status': 'error',
                'documents': [],
                'count': 0,
                'error': str(e)
            }

    def _is_duplicate(self, content: str) -> bool:
        """Check if content is already in knowledge base"""
        try:
            results = self.collection.query(
                query_texts=[content],
                n_results=1
            )
            if results and results['distances'][0]:
                return results['distances'][0][0] < 0.1  # Similarity threshold
            return False
        except:
            return False

    def add_to_knowledge_base(self, document: Dict[str, Any]) -> bool:
        """Add a new document to the knowledge base."""
        try:
            if not document.get('content'):
                logger.warning("Empty content in document")
                return False
            
            # Generate embedding based on model choice
            logger.info("Generating embedding...")
            if self.model_choice == "openai":
                embedding = self.openai_client.embeddings.create(
                    input=document['content'],
                    model="text-embedding-ada-002"
                ).data[0].embedding
            else:
                # Use Llama model for embeddings
                inputs = self.llama_tokenizer(
                    document['content'],
                    return_tensors="pt",
                    padding=True,
                    truncation=True
                ).to(self.llama_model.device)
                
                with torch.no_grad():
                    outputs = self.llama_model(**inputs)
                    embedding = outputs.last_hidden_state.mean(dim=1).squeeze().cpu().numpy()
            
            # Add to Chroma with embedding
            doc_id = str(uuid.uuid4())
            logger.info(f"Adding document with ID: {doc_id}")
            
            self.collection.add(
                documents=[document['content']],
                embeddings=[embedding],
                metadatas=[document['metadata']],
                ids=[doc_id]
            )
            
            # Verify document was added
            try:
                result = self.collection.get(ids=[doc_id])
                if result and len(result['documents']) > 0:
                    logger.info(f"Successfully added document: {document['metadata']['title']}")
                    return True
                else:
                    logger.warning("Document verification failed")
                    return False
            except Exception as e:
                logger.error(f"Error verifying document: {str(e)}")
                return False
            
        except Exception as e:
            logger.error(f"Error adding to knowledge base: {str(e)}")
            return False
        
    def generate_summary_with_llama(self, content: str) -> str:
        """Generate summary using Llama model"""
        try:
            prompt = f"Generate a brief, informative summary in 2-3 sentences of the following content:\n\n{content}"
            inputs = self.llama_tokenizer(prompt, return_tensors="pt").to(self.llama_model.device)
            
            with torch.no_grad():
                outputs = self.llama_model.generate(
                    inputs.input_ids,
                    max_length=200,
                    temperature=0.7,
                    num_return_sequences=1,
                    pad_token_id=self.llama_tokenizer.eos_token_id
                )
            
            summary = self.llama_tokenizer.decode(outputs[0], skip_special_tokens=True)
            return summary.strip()
            
        except Exception as e:
            logger.error(f"Error generating summary with Llama: {str(e)}")
            return "Summary generation failed"

    def clear_knowledge_base(self):
        """Clear all content from knowledge base"""
        try:
            # Delete existing collection
            try:
                self.chroma_client.delete_collection(name="knowledge_base")
                logger.info("Deleted existing knowledge base collection")
            except Exception as e:
                logger.info("No existing collection to delete")
            
            # Create new empty collection
            self.collection = self.chroma_client.create_collection(
                name="knowledge_base",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("Created new empty knowledge base collection")
            
            # Reset any model-specific caches or states
            if self.model_choice == "openai":
                # OpenAI doesn't maintain state, so no need to reset
                pass
            else:
                # Reset Llama model's cache if needed
                if hasattr(self, 'llama_model') and self.llama_model is not None:
                    self.llama_model.zero_grad(set_to_none=True)
                    torch.cuda.empty_cache()
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing knowledge base: {str(e)}")
            return False
    
