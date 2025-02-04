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
import glob
from ..models.search_types import ModelChoice
from django.conf import settings
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from pathlib import Path

logger = logging.getLogger(__name__)
MODEL_CHOICE = "openai"
KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parent.parent.parent / 'knowledge_base'

class HybridRAG:
    def __init__(self):
        """Initialize the RAG system"""
        self.model_choice = settings.AI_MODEL_CONFIG.get('USE_LLAMA', False)
        self.model_name = settings.AI_MODEL_CONFIG.get('OPENAI_MODEL', 'gpt-4')
        self.temperature = settings.AI_MODEL_CONFIG.get('TEMPERATURE', 0.7)
        
        # Ensure knowledge base directory exists
        KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Knowledge base directory: {KNOWLEDGE_BASE_DIR}")
        
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Set up paths
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.persist_directory = str(self.base_dir / 'data' / 'chroma_db')
        
        # Create directory if it doesn't exist
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=self.persist_directory
        )
        
        # Initialize or get collection
        self._initialize_empty_collection()
        
        # Store last query metadata
        self.last_query_metadata = {}
        
        # Load initial knowledge base
        self._load_knowledge_base()

    def generate_response(self, prompt: str, context: str = None, use_llama: bool = None) -> str:
        """Generate response using configured model"""
        # Use parameter if provided, otherwise use settings default
        use_llama = use_llama if use_llama is not None else self.model_choice
        
        try:
            system_prompt = """You are an AI assistant helping with data analysis and insights.
            Use the provided context to generate relevant and accurate responses."""

            if context:
                user_prompt = f"Context:\n{context}\n\nQuestion: {prompt}"
            else:
                user_prompt = prompt

            if use_llama:
                combined_prompt = f"{system_prompt}\n\nUser: {user_prompt}\nAssistant:"
                return get_llama_response(combined_prompt)
            else:
                response = self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=self.temperature
                )
                return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"Error generating response: {str(e)}"

    def _initialize_model(self):
        """Initialize the chosen model"""
        if self.model_choice == "openai":
            if not os.getenv('OPENAI_API_KEY'):
                raise ValueError("OpenAI API key not found in environment variables")
            self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.llama_model = None
            self.llama_tokenizer = None
        else:
            try:
                from transformers import AutoTokenizer, AutoModelForCausalLM
                import torch
                
                # Initialize Hugging Face's LLaMA
                model_name = "meta-llama/Llama-2-7b-chat-hf"
                auth_token = os.getenv('HUGGINGFACE_TOKEN')
                
                # Initialize tokenizer and model
                self.llama_tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    use_auth_token=auth_token
                )
                
                self.llama_model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    use_auth_token=auth_token,
                    torch_dtype=torch.float16,  # Use float16 for efficiency
                    device_map="auto"  # Automatically handle device placement
                )
                
                # Set model to evaluation mode
                self.llama_model.eval()
                logger.info("Successfully initialized LLaMA model")
                
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
                self.collection = self.chroma_client.get_or_create_collection(
                    name="knowledge_base",
                    metadata={"hnsw:space": "cosine"}
                )
                if reset:
                    self.chroma_client.delete_collection("knowledge_base")
                    self.collection = self.chroma_client.create_collection(
                        name="knowledge_base",
                        metadata={"hnsw:space": "cosine"}
                    )
            except Exception as e:
                logger.error(f"Error in collection initialization: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"Error initializing collection: {str(e)}")
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

    def get_factual_context(self, query: str, k: int = 3) -> str:
        """Get relevant context from knowledge base"""
        try:
            # Generate embedding for query using OpenAI
            query_embedding = self.openai_client.embeddings.create(
                input=query,
                model="text-embedding-ada-002"
            ).data[0].embedding
            
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Store metadata for later use
            self.last_query_metadata = {
                "documents": results["documents"][0],
                "metadata": results["metadatas"][0],
                "distances": results["distances"][0]
            }
            
            # Combine relevant documents into context
            context = "\n\n".join(results["documents"][0])
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting context: {str(e)}")
            return ""

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
            # Get relevant context
            context = self.get_factual_context(transcription)
            
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

            Context: {context}
            Conversation: {transcription}
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a concise analyst. Format your response with bullet points (•) and dashes (-)."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature
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
            logger.error(f"Error generating insights: {str(e)}")
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
                model=settings.GPT_MODEL_NAME,
                messages=[
                    {"role": "system", "content": """
                        You are an expert at synthesizing conversations and connecting them to organizational knowledge.
                        Focus on continuity with existing documentation and clear next steps.
                        Highlight any contradictions or updates needed in the knowledge base.
                    """},
                    {"role": "user", "content": prompt}
                ],
                temperature=settings.DEFAULT_TEMPERATURE,
                max_tokens=settings.DEFAULT_MAX_TOKENS
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
                model=settings.GPT_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "Identify knowledge base gaps and needed updates."},
                    {"role": "user", "content": prompt}
                ],
                temperature=settings.DEFAULT_TEMPERATURE
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
                model=settings.GPT_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are an expert at writing professional emails based on conversations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=settings.DEFAULT_TEMPERATURE
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
                model=settings.GPT_MODEL_NAME,
                messages=[
                    {"role": "system", "content": """
                        You are an expert at providing information from our knowledge base.
                        Be clear about what you know and what might need additional research.
                    """},
                    {"role": "user", "content": prompt}
                ],
                temperature=settings.DEFAULT_TEMPERATURE,
                max_tokens=settings.DEFAULT_MAX_TOKENS
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
        """Inspect the current state of the knowledge base"""
        try:
            all_docs = self.collection.get()
            return {
                'documents': all_docs['documents'],
                'count': len(all_docs['documents'])
            }
        except Exception as e:
            logger.error(f"Error inspecting collection: {str(e)}")
            return {'documents': [], 'count': 0}

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

    def add_to_knowledge_base(self, document: Dict[str, Any], save_to_file: bool = True) -> bool:
        """Add a new document to the knowledge base"""
        try:
            if not document.get('content'):
                logger.warning("Empty content in document")
                return False
            
            # Save to file if requested
            if save_to_file:
                file_path = KNOWLEDGE_BASE_DIR / f"learned_{int(time.time())}.txt"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(document['content'])
            
            # Generate embedding
            embedding = self.openai_client.embeddings.create(
                input=document['content'],
                model="text-embedding-ada-002"
            ).data[0].embedding
            
            # Add to ChromaDB
            doc_id = str(uuid.uuid4())
            self.collection.add(
                documents=[document['content']],
                embeddings=[embedding],
                metadatas=[{
                    **document['metadata'],
                    'file_path': str(file_path) if save_to_file else None
                }],
                ids=[doc_id]
            )
            
            return True
            
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

    def clear_knowledge_base(self) -> bool:
        """Clear all content from knowledge base"""
        try:
            self._initialize_empty_collection(reset=True)
            return True
        except Exception as e:
            logger.error(f"Error clearing knowledge base: {str(e)}")
            return False

    async def _load_knowledge_base(self):
        """Load documents from knowledge base directory"""
        try:
            # Get all text files from knowledge base directory
            knowledge_files = glob.glob(str(KNOWLEDGE_BASE_DIR / "**/*.txt"), recursive=True)
            logger.info(f"Found {len(knowledge_files)} knowledge base files")

            for file_path in knowledge_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read().strip()
                        if content:  # Only process non-empty files
                            # Generate embedding
                            embedding = self.openai_client.embeddings.create(
                                input=content,
                                model="text-embedding-ada-002"
                            ).data[0].embedding

                            # Add to ChromaDB with metadata
                            doc_id = str(uuid.uuid4())
                            self.collection.add(
                                documents=[content],
                                embeddings=[embedding],
                                metadatas=[{
                                    'source': str(file_path),
                                    'timestamp': time.time(),
                                    'type': 'knowledge_base'
                                }],
                                ids=[doc_id]
                            )
                            logger.info(f"Loaded knowledge base file: {file_path}")
                except Exception as e:
                    logger.error(f"Error processing knowledge base file {file_path}: {str(e)}")

        except Exception as e:
            logger.error(f"Error loading knowledge base: {str(e)}")
    
