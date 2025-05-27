# import sys
# import os
# import pdfplumber
# import numpy as np
# from sentence_transformers import SentenceTransformer
# import faiss
# import json

# def extract_text_from_pdf(pdf_path):
#     """Extract text from all pages of a PDF."""
#     text = ""
#     try:
#         with pdfplumber.open(pdf_path) as pdf:
#             for page in pdf.pages:
#                 text += page.extract_text() or ""
#     except Exception as e:
#         print(f"Error extracting text from PDF: {e}")
#     return text

# def main(pdf_path, profile_id):
#     # Load pre-trained sentence transformer model
#     model = SentenceTransformer('all-MiniLM-L6-v2')
    
#     # Extract text from PDF
#     text = extract_text_from_pdf(pdf_path)
#     if not text:
#         print("No text extracted from PDF")
#         return
    
#     # Split text into sentences (or chunks) for embedding
#     sentences = [s.strip() for s in text.split('. ') if s.strip()]
#     if not sentences:
#         print("No sentences to embed")
#         return
    
#     # Generate embeddings
#     embeddings = model.encode(sentences, convert_to_numpy=True)
    
#     # Initialize or load FAISS index
#     index_path = os.path.join('vectors', 'faiss_index.bin')
#     metadata_path = os.path.join('vectors', 'metadata.json')
    
#     dimension = embeddings.shape[1]  # Embedding dimension (384 for MiniLM)
#     if os.path.exists(index_path):
#         index = faiss.read_index(index_path)
#     else:
#         index = faiss.IndexFlatL2(dimension)
    
#     # Load or initialize metadata
#     if os.path.exists(metadata_path):
#         with open(metadata_path, 'r') as f:
#             metadata = json.load(f)
#     else:
#         metadata = []
    
#     # Add embeddings to FAISS index
#     start_idx = index.ntotal
#     index.add(embeddings)
    
#     # Update metadata with profile_id and sentence mappings
#     for i, sentence in enumerate(sentences):
#         metadata.append({
#             'profile_id': profile_id,
#             'sentence': sentence,
#             'index': start_idx + i
#         })
    
#     # Save FAISS index and metadata
#     faiss.write_index(index, index_path)
#     with open(metadata_path, 'w') as f:
#         json.dump(metadata, f, indent=2)
    
#     print(f"Vectorized PDF for profile {profile_id}")

# if __name__ == "__main__":
#     if len(sys.argv) != 3:
#         print("Usage: python vectorize_pdf.py <pdf_path> <profile_id>")
#         sys.exit(1)
#     pdf_path, profile_id = sys.argv[1], sys.argv[2]
#     main(pdf_path, profile_id)












# import sys
# import os
# import pdfplumber
# import numpy as np
# from sentence_transformers import SentenceTransformer
# import faiss
# import json

# def extract_text_from_pdf(pdf_path):
#     """Extract text from all pages of a PDF."""
#     text = ""
#     try:
#         with pdfplumber.open(pdf_path) as pdf:
#             for page in pdf.pages:
#                 page_text = page.extract_text() or ""
#                 text += page_text
#                 print(f"Extracted text from page {page.page_number}: {page_text[:100]}...")  # Debug
#     except Exception as e:
#         print(f"Error extracting text from PDF: {e}")
#     print(f"Total extracted text: {text[:200]}...")  # Debug
#     return text

# def main(pdf_path, profile_id):
#     print(f"Processing PDF: {pdf_path}, Profile ID: {profile_id}")  # Debug
#     # Verify PDF exists
#     if not os.path.exists(pdf_path):
#         print(f"Error: PDF file {pdf_path} does not exist")
#         sys.exit(1)

#     # Load pre-trained sentence transformer model
#     try:
#         print("Loading SentenceTransformer model...")  # Debug
#         model = SentenceTransformer('all-MiniLM-L6-v2')
#         print("Model loaded successfully")
#     except Exception as e:
#         print(f"Error loading model: {e}")
#         sys.exit(1)
    
#     # Extract text from PDF
#     text = extract_text_from_pdf(pdf_path)
#     if not text.strip():
#         print("No text extracted from PDF")
#         sys.exit(1)
    
#     # Split text into sentences (or chunks) for embedding
#     sentences = [s.strip() for s in text.split('. ') if s.strip()]
#     print(f"Extracted sentences: {sentences}")  # Debug
#     if not sentences:
#         print("No sentences to embed")
#         sys.exit(1)
    
#     # Generate embeddings
#     try:
#         print("Generating embeddings...")  # Debug
#         embeddings = model.encode(sentences, convert_to_numpy=True)
#         print(f"Generated {len(embeddings)} embeddings, shape: {embeddings.shape}")
#     except Exception as e:
#         print(f"Error generating embeddings: {e}")
#         sys.exit(1)
    
#     # Initialize or load FAISS index
#     index_path = os.path.join('vectors', 'faiss_index.bin')
#     metadata_path = os.path.join('vectors', 'metadata.json')
    
#     try:
#         os.makedirs('vectors', exist_ok=True)
#         print(f"Ensured vectors directory exists: {os.path.abspath('vectors')}")  # Debug
#     except Exception as e:
#         print(f"Error creating vectors directory: {e}")
#         sys.exit(1)
    
#     dimension = embeddings.shape[1]  # Embedding dimension (384 for MiniLM)
#     if os.path.exists(index_path):
#         try:
#             index = faiss.read_index(index_path)
#             print(f"Loaded existing FAISS index with {index.ntotal} vectors")
#         except Exception as e:
#             print(f"Error loading FAISS index: {e}")
#             sys.exit(1)
#     else:
#         index = faiss.IndexFlatL2(dimension)
#         print("Created new FAISS index")
    
#     # Load or initialize metadata
#     if os.path.exists(metadata_path):
#         try:
#             with open(metadata_path, 'r') as f:
#                 metadata = json.load(f)
#             print(f"Loaded metadata with {len(metadata)} entries")
#         except Exception as e:
#             print(f"Error loading metadata: {e}")
#             sys.exit(1)
#     else:
#         metadata = []
#         print("Initialized empty metadata")
    
#     # Add embeddings to FAISS index
#     start_idx = index.ntotal
#     try:
#         index.add(embeddings)
#         print(f"Added {len(embeddings)} vectors to FAISS index, new total: {index.ntotal}")
#     except Exception as e:
#         print(f"Error adding vectors to FAISS index: {e}")
#         sys.exit(1)
    
#     # Update metadata with profile_id and sentence mappings
#     for i, sentence in enumerate(sentences):
#         metadata.append({
#             'profile_id': profile_id,
#             'sentence': sentence,
#             'index': start_idx + i
#         })
#     print(f"Updated metadata with {len(sentences)} new entries")
    
#     # Save FAISS index and metadata
#     try:
#         faiss.write_index(index, index_path)
#         print(f"Saved FAISS index to {index_path}")
#     except Exception as e:
#         print(f"Error saving FAISS index: {e}")
#         sys.exit(1)
    
#     try:
#         with open(metadata_path, 'w') as f:
#             json.dump(metadata, f, indent=2)
#         print(f"Saved metadata to {metadata_path}")
#     except Exception as e:
#         print(f"Error saving metadata: {e}")
#         sys.exit(1)
    
#     print(f"Vectorized PDF for profile {profile_id}")

# if __name__ == "__main__":
#     if len(sys.argv) != 3:
#         print("Usage: python vectorize_pdf.py <pdf_path> <profile_id>")
#         sys.exit(1)
#     pdf_path, profile_id = sys.argv[1], sys.argv[2]
#     main(pdf_path, profile_id)











# working and commenting on 22may due to openai
# import sys
# import os
# import pdfplumber
# import numpy as np
# from sentence_transformers import SentenceTransformer
# import faiss
# import json

# def extract_text_from_pdf(pdf_path):
#     text = ""
#     try:
#         with pdfplumber.open(pdf_path) as pdf:
#             for page in pdf.pages:
#                 text += page.extract_text() or ""
#     except Exception as e:
#         print(f"Error extracting text from PDF: {e}")
#     return text

# def main(pdf_path, profile_id):
#     model = SentenceTransformer('all-MiniLM-L6-v2')
#     text = extract_text_from_pdf(pdf_path)
#     if not text:
#         print("No text extracted from PDF")
#         return
    
#     # Split by newlines
#     sentences = [s.strip() for s in text.split('\n') if s.strip()]
#     if not sentences:
#         print("No sentences to embed")
#         return
    
#     embeddings = model.encode(sentences, convert_to_numpy=True)
#     index_path = os.path.join('vectors', 'faiss_index.bin')
#     metadata_path = os.path.join('vectors', 'metadata.json')
    
#     dimension = embeddings.shape[1]
#     if os.path.exists(index_path):
#         index = faiss.read_index(index_path)
#     else:
#         index = faiss.IndexFlatL2(dimension)
    
#     if os.path.exists(metadata_path):
#         with open(metadata_path, 'r') as f:
#             metadata = json.load(f)
#     else:
#         metadata = []
    
#     start_idx = index.ntotal
#     index.add(embeddings)
    
#     for i, sentence in enumerate(sentences):
#         metadata.append({
#             'profile_id': profile_id,
#             'sentence': sentence,
#             'index': start_idx + i
#         })
    
#     faiss.write_index(index, index_path)
#     with open(metadata_path, 'w') as f:
#         json.dump(metadata, f, indent=2)
    
#     print(f"Vectorized PDF for profile {profile_id}")

# if __name__ == "__main__":
#     if len(sys.argv) != 3:
#         print("Usage: python vectorize_pdf.py <pdf_path> <profile_id>")
#         sys.exit(1)
#     pdf_path, profile_id = sys.argv[1], sys.argv[2]
#     main(pdf_path, profile_id)



# import pdfplumber
# import json
# import os
# import sys
# from openai import OpenAI
# from dotenv import load_dotenv
# import psycopg2
# from psycopg2.extras import RealDictCursor

# # Load environment variables
# load_dotenv()
# OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# # Database configuration
# DB_CONFIG = {
#     'dbname': os.getenv('DB_NAME', 'profiledb'),
#     'user': os.getenv('DB_USER', 'postgres'),
#     'password': os.getenv('DB_PASSWORD', '123'),
#     'host': os.getenv('DB_HOST', 'localhost'),
#     'port': os.getenv('DB_PORT', '5432')
# }

# # Initialize Open AI client
# client = OpenAI(api_key=OPENAI_API_KEY)

# def get_db_connection():
#     try:
#         return psycopg2.connect(**DB_CONFIG)
#     except Exception as e:
#         print(f"Error connecting to database: {e}")
#         return None

# def chunk_text(text, max_tokens=1000):
#     words = text.split()
#     chunks = []
#     current_chunk = []
#     current_tokens = 0
#     for word in words:
#         current_chunk.append(word)
#         current_tokens += len(word) // 4 + 1  # Rough token estimate
#         if current_tokens >= max_tokens:
#             chunks.append(' '.join(current_chunk))
#             current_chunk = []
#             current_tokens = 0
#     if current_chunk:
#         chunks.append(' '.join(current_chunk))
#     return chunks

# def get_embedding(text):
#     try:
#         response = client.embeddings.create(
#             input=text,
#             model='text-embedding-ada-002'
#         )
#         return response.data[0].embedding
#     except Exception as e:
#         print(f"Error generating embedding: {e}")
#         return None

# def store_embeddings(profile_id, chunks, embeddings):
#     conn = get_db_connection()
#     if not conn:
#         return
#     try:
#         cursor = conn.cursor()
#         cursor.execute('CREATE TABLE IF NOT EXISTS embeddings (profile_id UUID, chunk TEXT, embedding JSONB)')
#         for chunk, embedding in zip(chunks, embeddings):
#             cursor.execute(
#                 'INSERT INTO embeddings (profile_id, chunk, embedding) VALUES (%s, %s, %s)',
#                 (profile_id, chunk, json.dumps(embedding))
#             )
#         conn.commit()
#     except Exception as e:
#         print(f"Error storing embeddings: {e}")
#     finally:
#         cursor.close()
#         conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) != 3:
#         print('Usage: python vectorize_pdf.py <pdf_path> <profile_id>')
#         sys.exit(1)

#     pdf_path = sys.argv[1]
#     profile_id = sys.argv[2]

#     # Extract text from PDF
#     try:
#         with pdfplumber.open(pdf_path) as pdf:
#             text = ''.join(page.extract_text() or '' for page in pdf.pages)
#     except Exception as e:
#         print(f"Error extracting PDF text: {e}")
#         sys.exit(1)

#     # Chunk text
#     chunks = chunk_text(text)
#     if not chunks:
#         print("No text extracted from PDF")
#         sys.exit(1)

#     # Generate embeddings
#     embeddings = []
#     for chunk in chunks:
#         embedding = get_embedding(chunk)
#         if embedding:
#             embeddings.append(embedding)
#         else:
#             print("Failed to generate embedding for chunk")
#             sys.exit(1)

#     # Store embeddings
#     store_embeddings(profile_id, chunks, embeddings)
#     print("Embeddings stored successfully")


# import sys
# import os
# import pdfplumber
# import json
# import psycopg2
# from openai import OpenAI
# from dotenv import load_dotenv

# load_dotenv()

# DB_CONFIG = {
#     'dbname': os.getenv('DB_NAME', 'profiledb'),
#     'user': os.getenv('DB_USER', 'profile'),
#     'password': os.getenv('DB_PASSWORD', 'profileUYh$13#'),
#     'host': os.getenv('DB_HOST', '122.176.158.168'),
#     'port': os.getenv('DB_PORT', '5432'),
#     'sslmode': 'require'
# }

# client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# def get_embedding(text):
#     try:
#         response = client.embeddings.create(input=text, model='text-embedding-ada-002')
#         return response.data[0].embedding
#     except Exception as e:
#         print(f"Embedding error: {e}", file=sys.stderr)
#         raise

# def main(pdf_path, profile_id):
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         # Create embeddings table if not exists
#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS embeddings (
#                 id SERIAL PRIMARY KEY,
#                 profile_id UUID NOT NULL,
#                 chunk TEXT NOT NULL,
#                 embedding JSONB NOT NULL
#             )
#         """)
#         conn.commit()

#         # Extract text from PDF
#         text = ''
#         with pdfplumber.open(pdf_path) as pdf:
#             for page in pdf.pages:
#                 text += page.extract_text() or ''
#         if not text:
#             print("No text extracted from PDF", file=sys.stderr)
#             sys.exit(1)

#         # Split text into chunks (e.g., by paragraph)
#         chunks = text.split('\n\n')
#         chunks = [chunk.strip() for chunk in chunks if chunk.strip()]

#         # Store embeddings
#         for chunk in chunks:
#             embedding = get_embedding(chunk)
#             cursor.execute(
#                 "INSERT INTO embeddings (profile_id, chunk, embedding) VALUES (%s, %s, %s)",
#                 (profile_id, chunk, json.dumps(embedding))
#             )
#         conn.commit()
#         print("Embeddings stored successfully")
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) != 3:
#         print("Error: PDF path and profile ID required", file=sys.stderr)
#         sys.exit(1)
#     pdf_path, profile_id = sys.argv[1], sys.argv[2]
#     main(pdf_path, profile_id)

import sys
import os
import pdfplumber
import json
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'profiledb'),
    'user': os.getenv('DB_USER', 'profile'),
    'password': os.getenv('DB_PASSWORD', 'profileUYh$13#'),
    'host': os.getenv('DB_HOST', '122.176.158.168'),
    'port': os.getenv('DB_PORT', '5432'),
    'sslmode': 'require'
}

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def get_embedding(text):
    try:
        response = client.embeddings.create(input=text, model='text-embedding-ada-002')
        return response.data[0].embedding
    except Exception as e:
        print(f"Embedding error: {e}", file=sys.stderr)
        raise

def main(pdf_path, profile_id):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id SERIAL PRIMARY KEY,
                profile_id UUID NOT NULL,
                chunk TEXT NOT NULL,
                embedding JSONB NOT NULL
            )
        """)
        conn.commit()

        text = ''
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
        text = text.strip()
        if not text:
            print("No text extracted from PDF", file=sys.stderr)
            sys.exit(1)

        chunks = text.split('\n\n')
        chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
        if not chunks:
            chunks = [text]
        print(f"Extracted {len(chunks)} chunks", file=sys.stderr)

        for chunk in chunks:
            embedding = get_embedding(chunk)
            cursor.execute(
                "INSERT INTO embeddings (profile_id, chunk, embedding) VALUES (%s, %s, %s)",
                (profile_id, chunk, json.dumps(embedding))
            )
        conn.commit()
        print("Embeddings stored successfully")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Error: PDF path and profile ID required", file=sys.stderr)
        sys.exit(1)
    pdf_path, profile_id = sys.argv[1], sys.argv[2]
    main(pdf_path, profile_id)