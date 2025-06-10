
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