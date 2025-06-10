
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import json
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Centralized database configuration
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}
print("DB_CONFIG:", DB_CONFIG)

def get_db_connection():
    """Create a database connection using centralized config."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("Database connection successful")
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def get_profile_id_by_name(name):
    """Fetch profile_id from profiledb based on name."""
    print(f"Fetching profile_id for name: {name}")
    conn = get_db_connection()
    if not conn:
        print("No database connection")
        return None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id FROM profiles WHERE LOWER(name) = LOWER(%s)", (name,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        profile_id = result['id'] if result else None
        print(f"Profile ID: {profile_id}")
        return profile_id
    except Exception as e:
        print(f"Error fetching profile_id: {e}")
        conn.close()
        return None

def extract_profile_name(query_text):
    """Extract potential profile name from query by checking profiles table."""
    print(f"Extracting profile name from query: {query_text}")
    conn = get_db_connection()
    if not conn:
        print("No database connection for name extraction")
        return None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT name FROM profiles")
        known_names = [row['name'].lower() for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        print(f"Known names: {known_names}")
        
        words = re.findall(r'\w+', query_text.lower())
        for word in words:
            if word in known_names:
                print(f"Found profile name: {word}")
                return word
        print("No profile name found")
        return None
    except Exception as e:
        print(f"Error fetching profile names: {e}")
        conn.close()
        return None

def query_faiss(query_text, top_k=15, max_distance=4.0):
    print(f"Processing query: {query_text}")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    index_path = 'vectors/faiss_index.bin'
    metadata_path = 'vectors/metadata.json'

    try:
        index = faiss.read_index(index_path)
        print("FAISS index loaded")
    except Exception as e:
        print(f"Error reading FAISS index: {e}")
        return []

    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        print(f"Metadata loaded with {len(metadata)} entries")
    except Exception as e:
        print(f"Error reading metadata: {e}")
        return []

    metadata_map = {entry['index']: entry for entry in metadata}
    
    query_embedding = model.encode([query_text], convert_to_numpy=True)
    distances, indices = index.search(query_embedding, top_k)
    print(f"FAISS search returned {len(indices[0])} results")

    # Log raw FAISS results
    print("Raw FAISS results:")
    for idx, dist in zip(indices[0], distances[0]):
        if idx in metadata_map:
            entry = metadata_map[idx]
            print(f"Index: {idx}, Profile ID: {entry['profile_id']}, Sentence: {entry['sentence']}, Distance: {dist}")

    # Extract profile name and keywords
    profile_name = extract_profile_name(query_text)
    profile_id = get_profile_id_by_name(profile_name) if profile_name else None
    keywords = [word.lower() for word in re.findall(r'\w+', query_text) if word.lower() not in ['of', profile_name] if profile_name]
    print(f"Profile name: {profile_name}, Profile ID: {profile_id}, Keywords: {keywords}")

    results = []
    for idx, dist in zip(indices[0], distances[0]):
        if idx in metadata_map and dist <= max_distance:
            entry = metadata_map[idx]
            sentence = entry['sentence'].lower()
            profile_match = profile_id is None or entry['profile_id'] == profile_id
            keyword_match = not keywords or any(keyword in sentence for keyword in keywords)
            print(f"Evaluating: Profile ID: {entry['profile_id']}, Sentence: {entry['sentence']}, Distance: {dist}, Profile Match: {profile_match}, Keyword Match: {keyword_match}")
            if profile_match and keyword_match:
                results.append({
                    'profile_id': entry['profile_id'],
                    'sentence': entry['sentence'],
                    'distance': float(dist)
                })
                print(f"Match found: {entry['sentence']}, Distance: {dist}")
    print(f"Returning {len(results)} results")
    return results

if __name__ == "__main__":
    query = "What are Skills of Arun"
    results = query_faiss(query)
    for result in results:
        print(f"Profile: {result['profile_id']}, Sentence: {result['sentence']}, Distance: {result['distance']}")

       