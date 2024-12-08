import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["POSTHOG_DISABLED"] = "1"

import re
from pathlib import Path
from openai import OpenAI
import chromadb

def txt_to_sentences(txt_path):
    try:
        # Read the txt file
        with open(txt_path, 'r', encoding='utf-8') as file:
            text = file.read()
            
            # Split into sentences
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
            
            # Clean up sentences
            sentences = [s.strip() for s in sentences if s.strip()]
            
            return sentences
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        raise

# Initialize OpenAI client
client = OpenAI()

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_data")

# Create collection
collection = chroma_client.get_or_create_collection(name="knowledge_base")

# Load and process document
txt_path = "/home/ubuntu/django_project/text.txt"
documents = txt_to_sentences(txt_path)

# Get embeddings from OpenAI
embeddings = [
    client.embeddings.create(
        input=doc,
        model="text-embedding-3-small"
    ).data[0].embedding for doc in documents
]

# Generate IDs
doc_ids = [f"doc{i}" for i in range(len(documents))]

# Add to collection
collection.add(
    documents=documents,
    embeddings=embeddings,
    ids=doc_ids
)

print(f"Successfully processed and stored {len(documents)} sentences.")

'''
import docx2txt  # Simpler library for DOCX files
import re
from pathlib import Path
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions

def verify_file_access(file_path):
    try:
        with open(file_path, 'rb') as f:
            first_bytes = f.read(4)
            is_zip = first_bytes.startswith(b'PK\x03\x04')
            print(f"File can be opened: True")
            print(f"File appears to be ZIP/DOCX format: {is_zip}")
    except Exception as e:
        print(f"Error reading file: {str(e)}")

def doc_to_sentences(doc_path):
    try:
        # Extract text using docx2txt instead of textract
        text = docx2txt.process(doc_path)
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        
        # Clean up sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        raise

# Initialize OpenAI client
client = OpenAI()

# Initialize ChromaDB with a simpler configuration
chroma_client = chromadb.PersistentClient(path="./chroma_data")

# Create or get collection without OpenAI embeddings initially
collection = chroma_client.get_or_create_collection(
    name="knowledge_base"
)

# Load and process document
doc_path = "/home/ubuntu/django_project/text.docx"
verify_file_access(doc_path)  # Verify file first
documents = doc_to_sentences(doc_path)

# Get embeddings
embeddings = [
    client.embeddings.create(
        input=doc,
        model="text-embedding-3-small"
    ).data[0].embedding for doc in documents
]

# Generate IDs
doc_ids = [f"doc{i}" for i in range(len(documents))]

# Add to collection
collection.add(
    documents=documents,
    embeddings=embeddings,
    ids=doc_ids
)

# Query processing remains the same
query = "What does the document say?"  # Modify this query based on your needs
query_embedding = client.embeddings.create(
    input=query,
    model="text-embedding-3-small"
).data[0].embedding

results = collection.query(query_embeddings=[query_embedding], n_results=2)
retrieved_documents = results["documents"][0]

# Generate response
context = "\n".join(retrieved_documents)
prompt = f"""
Use the following context to answer the question:
Context: {context}
Question: {query}
Answer:
"""

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a knowledgeable assistant."},
        {"role": "user", "content": prompt}
    ],
    max_tokens=200,
    temperature=0.5
)

print("Answer:", response.choices[0].message.content)
'''
'''
from sentence_transformers import SentenceTransformer
import chromadb
from openai import OpenAI

# Initialize OpenAI client (only for final completion)
client = OpenAI()

# Initialize local embedding model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_data")

# Create collection with local embedding function
collection = chroma_client.get_or_create_collection(
    name="knowledge_base",
    embedding_function=lambda texts: embedding_model.encode(texts).tolist()
)

# Documents
documents = [
    "The Eiffel Tower is located in Paris, France.",
    "Python is a versatile programming language.",
    "OpenAI provides advanced AI models."
]

# Add documents (embeddings are generated automatically)
collection.add(
    documents=documents,
    ids=["doc1", "doc2", "doc3"]
)

# User query
query = "Where is the Eiffel Tower located?"

# Query using local embeddings
results = collection.query(
    query_texts=[query],
    n_results=2
)

# Get retrieved documents
retrieved_documents = results["documents"][0]

# Use OpenAI GPT for the final response
context = "\n".join(retrieved_documents)
prompt = f"""
Use the following context to answer the question:
Context: {context}
Question: {query}
Answer:
"""

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a knowledgeable assistant."},
        {"role": "user", "content": prompt}
    ],
    max_tokens=200,
    temperature=0.5
)

print("Answer:", response.choices[0].message.content)
'''