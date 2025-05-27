# import numpy as np
# from sentence_transformers import SentenceTransformer
# import faiss
# import json

# def query_faiss(query_text, top_k=5):
#     model = SentenceTransformer('all-MiniLM-L6-v2')
#     index_path = 'vectors/faiss_index.bin'
#     metadata_path = 'vectors/metadata.json'

#     index = faiss.read_index(index_path)
#     with open(metadata_path, 'r') as f:
#         metadata = json.load(f)

#     query_embedding = model.encode([query_text], convert_to_numpy=True)
#     distances, indices = index.search(query_embedding, top_k)

#     results = []
#     for idx, dist in zip(indices[0], distances[0]):
#         if idx < len(metadata):
#             results.append({
#                 'profile_id': metadata[idx]['profile_id'],
#                 'sentence': metadata[idx]['sentence'],
#                 'distance': float(dist)
#             })
#     return results

# if __name__ == "__main__":
#     query = "CSS skills"
#     results = query_faiss(query)
#     for result in results:
#         print(f"Profile: {result['profile_id']}, Sentence: {result['sentence']}, Distance: {result['distance']}")















#below code working perfect as giving
# when query = "CSS skills"
# (venv) C:\Users\rajes_y5mztzq\OneDrive\Desktop\my\profile-management\backend>python query_faiss.py
# Profile: 8a90bb79-7997-4870-9ece-1ecc69c73b4b, Sentence: Name: Arun
# Address: Gurugram
# Qualification: B Tech
# Skills: CSS,JS, Distance: 1.1344759464263916

# when query = "CSS, React"
# (venv) C:\Users\rajes_y5mztzq\OneDrive\Desktop\my\profile-management\backend>python query_faiss.py
# Profile: 8a90bb79-7997-4870-9ece-1ecc69c73b4b, Sentence: Skills: React,Node, Distance: 0.8361594080924988
# Profile: 8a90bb79-7997-4870-9ece-1ecc69c73b4b, Sentence: Name: Arun
# Address: Gurugram
# Qualification: B Tech
# Skills: CSS,JS, Distance: 1.557901382446289


# import numpy as np
# from sentence_transformers import SentenceTransformer
# import faiss
# import json

# def query_faiss(query_text, top_k=5):
#     model = SentenceTransformer('all-MiniLM-L6-v2')
#     index_path = 'vectors/faiss_index.bin'
#     metadata_path = 'vectors/metadata.json'

#     index = faiss.read_index(index_path)
#     with open(metadata_path, 'r') as f:
#         metadata = json.load(f)

#     # Create a map of valid indices
#     metadata_map = {entry['index']: entry for entry in metadata}
    
#     query_embedding = model.encode([query_text], convert_to_numpy=True)
#     distances, indices = index.search(query_embedding, top_k)

#     results = []
#     for idx, dist in zip(indices[0], distances[0]):
#         if idx in metadata_map:  # Only include valid indices
#             entry = metadata_map[idx]
#             results.append({
#                 'profile_id': entry['profile_id'],
#                 'sentence': entry['sentence'],
#                 'distance': float(dist)
#             })
#     return results

# if __name__ == "__main__":
#     # query = "CSS skills"
#     # query = "CSS and Bootstrap"
#     query = "Skills of Arun"
#     # query = "CSS, React"
#     results = query_faiss(query)
#     for result in results:
#         print(f"Profile: {result['profile_id']}, Sentence: {result['sentence']}, Distance: {result['distance']}")
















# import numpy as np
# import faiss
# import json

# def list_all_vectors():
#     index_path = 'vectors/faiss_index.bin'
#     metadata_path = 'vectors/metadata.json'
#     try:
#         index = faiss.read_index(index_path)
#         with open(metadata_path, 'r') as f:
#             metadata = json.load(f)
#         print(f"Total Vectors in faiss_index.bin: {index.ntotal}")
#         for entry in metadata:
#             print(f"Index: {entry['index']}, Profile: {entry['profile_id']}, Sentence: {entry['sentence']}")
#     except FileNotFoundError:
#         print("Error: faiss_index.bin or metadata.json not found")
#     except Exception as e:
#         print(f"Error: {str(e)}")

# if __name__ == "__main__":
#     list_all_vectors()

# Got output as (venv) C:\Users\rajes_y5mztzq\OneDrive\Desktop\my\profile-management\backend>python query_faiss.py
# Total Vectors in faiss_index.bin: 1
# Index: 0, Profile: 3bd99008-8bc5-492b-981a-4b50af763936, Sentence: Name: Arun
# Address: Gurugram
# Qualification: B Tech
# Skills: CSS,JS    




# import json

# def list_all_vectorized_data():
#     metadata_path = 'vectors/metadata.json'
    
#     try:
#         with open(metadata_path, 'r') as f:
#             metadata = json.load(f)
        
#         if not metadata:
#             print("No vectorized data found in metadata.json")
#             return
        
#         print("All Vectorized Data:")
#         for entry in metadata:
#             print(f"Profile: {entry['profile_id']}, Sentence: {entry['sentence']}, Index: {entry['index']}")
    
#     except FileNotFoundError:
#         print("Error: metadata.json not found in vectors/")
#     except json.JSONDecodeError:
#         print("Error: metadata.json is corrupted or invalid")
#     except Exception as e:
#         print(f"Error: {str(e)}")

# if __name__ == "__main__":
#     list_all_vectorized_data()



# import numpy as np
# import faiss
# import json

# def list_all_vectors():
#     index_path = 'vectors/faiss_index.bin'
#     metadata_path = 'vectors/metadata.json'
    
#     try:
#         # Load FAISS index and metadata
#         index = faiss.read_index(index_path)
#         with open(metadata_path, 'r') as f:
#             metadata = json.load(f)
        
#         if not metadata:
#             print("No vectorized data found")
#             return
        
#         # Get all vectors from FAISS index
#         total_vectors = index.ntotal
#         vectors = index.reconstruct_n(0, total_vectors)  # Extract all vectors
        
#         print("All Vectorized Data:")
#         for i, entry in enumerate(metadata):
#             vector = vectors[entry['index']]
#             print(f"Profile: {entry['profile_id']}, Sentence: {entry['sentence']}, Index: {entry['index']}")
#             print(f"Vector (first 5 dimensions): {vector[:5]}... (total {len(vector)} dimensions)")
#             print("-" * 50)
    
#     except FileNotFoundError:
#         print("Error: faiss_index.bin or metadata.json not found")
#     except Exception as e:
#         print(f"Error: {str(e)}")

# if __name__ == "__main__":
#     list_all_vectors()







# import numpy as np
# from sentence_transformers import SentenceTransformer
# import faiss
# import json
# import re
# import psycopg2
# from psycopg2.extras import RealDictCursor
# from dotenv import load_dotenv
# import os

# # Load environment variables
# load_dotenv()

# # Centralized database configuration
# DB_CONFIG = {
#     'dbname': os.getenv('DB_NAME'),
#     'user': os.getenv('DB_USER'),
#     'password': os.getenv('DB_PASSWORD'),
#     'host': os.getenv('DB_HOST'),
#     'port': os.getenv('DB_PORT')
# }


# def get_db_connection():
#     """Create a database connection using centralized config."""
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         return conn
#     except Exception as e:
#         print(f"Error connecting to database: {e}")
#         return None
# # # Add after load_dotenv()
# # print("DB_CONFIG:", DB_CONFIG)
# # conn = get_db_connection()
# # print("Connection successful:", conn is not None)
# # if conn:
# #     conn.close()

# def get_profile_id_by_name(name):
#     """Fetch profile_id from profiledb based on name."""
#     conn = get_db_connection()
#     if not conn:
#         return None
#     try:
#         cursor = conn.cursor(cursor_factory=RealDictCursor)
#         cursor.execute("SELECT id FROM profiles WHERE LOWER(name) = LOWER(%s)", (name,))
#         result = cursor.fetchone()
#         cursor.close()
#         conn.close()
#         return result['id'] if result else None
#     except Exception as e:
#         print(f"Error fetching profile_id: {e}")
#         conn.close()
#         return None

# def extract_profile_name(query_text):
#     """Extract potential profile name from query by checking profiles table."""
#     conn = get_db_connection()
#     if not conn:
#         return None
#     try:
#         cursor = conn.cursor(cursor_factory=RealDictCursor)
#         cursor.execute("SELECT name FROM profiles")
#         known_names = [row['name'].lower() for row in cursor.fetchall()]
#         cursor.close()
#         conn.close()
        
#         words = re.findall(r'\w+', query_text.lower())
#         for word in words:
#             if word in known_names:
#                 return word
#         return None
#     except Exception as e:
#         print(f"Error fetching profile names: {e}")
#         conn.close()
#         return None

# def query_faiss(query_text, top_k=5, max_distance=1.3):
#     model = SentenceTransformer('all-MiniLM-L6-v2')
#     index_path = 'vectors/faiss_index.bin'
#     metadata_path = 'vectors/metadata.json'

#     try:
#         index = faiss.read_index(index_path)
#     except Exception as e:
#         print(f"Error reading FAISS index: {e}")
#         return []

#     try:
#         with open(metadata_path, 'r') as f:
#             metadata = json.load(f)
#     except Exception as e:
#         print(f"Error reading metadata: {e}")
#         return []

#     metadata_map = {entry['index']: entry for entry in metadata}
    
#     query_embedding = model.encode([query_text], convert_to_numpy=True)
#     distances, indices = index.search(query_embedding, top_k)

#     # Extract profile name and keywords
#     profile_name = extract_profile_name(query_text)
#     profile_id = get_profile_id_by_name(profile_name) if profile_name else None
#     keywords = [word.lower() for word in re.findall(r'\w+', query_text) if word.lower() not in ['of', profile_name] if profile_name]

#     results = []
#     for idx, dist in zip(indices[0], distances[0]):
#         if idx in metadata_map and dist <= max_distance:
#             entry = metadata_map[idx]
#             sentence = entry['sentence'].lower()
#             # Filter by profile_id (if specified) and keywords
#             if (profile_id is None or entry['profile_id'] == profile_id) and (not keywords or any(keyword in sentence for keyword in keywords)):
#                 results.append({
#                     'profile_id': entry['profile_id'],
#                     'sentence': entry['sentence'],
#                     'distance': float(dist)
#                 })
#     return results

# if __name__ == "__main__":
#     query = "Skills of Arun"
#     results = query_faiss(query)
#     for result in results:
#         print(f"Profile: {result['profile_id']}, Sentence: {result['sentence']}, Distance: {result['distance']}")



# import numpy as np
# from sentence_transformers import SentenceTransformer
# import faiss
# import json
# import re
# import psycopg2
# from psycopg2.extras import RealDictCursor
# from dotenv import load_dotenv
# import os

# # Load environment variables
# load_dotenv()

# # Centralized database configuration
# DB_CONFIG = {
#     'dbname': os.getenv('DB_NAME'),
#     'user': os.getenv('DB_USER'),
#     'password': os.getenv('DB_PASSWORD'),
#     'host': os.getenv('DB_HOST'),
#     'port': os.getenv('DB_PORT')
# }
# print("DB_CONFIG:", DB_CONFIG)  # Moved here, after DB_CONFIG definition

# def get_db_connection():
#     """Create a database connection using centralized config."""
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         print("Database connection successful")
#         return conn
#     except Exception as e:
#         print(f"Error connecting to database: {e}")
#         return None

# def get_profile_id_by_name(name):
#     """Fetch profile_id from profiledb based on name."""
#     print(f"Fetching profile_id for name: {name}")
#     conn = get_db_connection()
#     if not conn:
#         print("No database connection")
#         return None
#     try:
#         cursor = conn.cursor(cursor_factory=RealDictCursor)
#         cursor.execute("SELECT id FROM profiles WHERE LOWER(name) = LOWER(%s)", (name,))
#         result = cursor.fetchone()
#         cursor.close()
#         conn.close()
#         profile_id = result['id'] if result else None
#         print(f"Profile ID: {profile_id}")
#         return profile_id
#     except Exception as e:
#         print(f"Error fetching profile_id: {e}")
#         conn.close()
#         return None

# def extract_profile_name(query_text):
#     """Extract potential profile name from query by checking profiles table."""
#     print(f"Extracting profile name from query: {query_text}")
#     conn = get_db_connection()
#     if not conn:
#         print("No database connection for name extraction")
#         return None
#     try:
#         cursor = conn.cursor(cursor_factory=RealDictCursor)
#         cursor.execute("SELECT name FROM profiles")
#         known_names = [row['name'].lower() for row in cursor.fetchall()]
#         cursor.close()
#         conn.close()
#         print(f"Known names: {known_names}")
        
#         words = re.findall(r'\w+', query_text.lower())
#         for word in words:
#             if word in known_names:
#                 print(f"Found profile name: {word}")
#                 return word
#         print("No profile name found")
#         return None
#     except Exception as e:
#         print(f"Error fetching profile names: {e}")
#         conn.close()
#         return None

# # def query_faiss(query_text, top_k=5, max_distance=1.3):
# def query_faiss(query_text, top_k=5, max_distance=3.0):
#     print(f"Processing query: {query_text}")
#     model = SentenceTransformer('all-MiniLM-L6-v2')
#     index_path = 'vectors/faiss_index.bin'
#     metadata_path = 'vectors/metadata.json'

#     try:
#         index = faiss.read_index(index_path)
#         print("FAISS index loaded")
#     except Exception as e:
#         print(f"Error reading FAISS index: {e}")
#         return []

#     try:
#         with open(metadata_path, 'r') as f:
#             metadata = json.load(f)
#         print(f"Metadata loaded with {len(metadata)} entries")
#     except Exception as e:
#         print(f"Error reading metadata: {e}")
#         return []

#     metadata_map = {entry['index']: entry for entry in metadata}
    
#     query_embedding = model.encode([query_text], convert_to_numpy=True)
#     distances, indices = index.search(query_embedding, top_k)
#     print(f"FAISS search returned {len(indices[0])} results")

#     # Extract profile name and keywords
#     profile_name = extract_profile_name(query_text)
#     profile_id = get_profile_id_by_name(profile_name) if profile_name else None
#     keywords = [word.lower() for word in re.findall(r'\w+', query_text) if word.lower() not in ['of', profile_name] if profile_name]
#     print(f"Profile name: {profile_name}, Profile ID: {profile_id}, Keywords: {keywords}")

#     results = []
#     for idx, dist in zip(indices[0], distances[0]):
#         if idx in metadata_map and dist <= max_distance:
#             entry = metadata_map[idx]
#             sentence = entry['sentence'].lower()
#             # Filter by profile_id (if specified) and keywords
#             # if (profile_id is None or entry['profile_id'] == profile_id) and (not keywords or any(keyword in sentence for keyword in keywords)):
#             if (profile_id is None or entry['profile_id'] == profile_id):  # Remove keyword check
#                 results.append({
#                     'profile_id': entry['profile_id'],
#                     'sentence': entry['sentence'],
#                     'distance': float(dist)
#                 })
#                 print(f"Match found: {entry['sentence']}, Distance: {dist}")
#     print(f"Returning {len(results)} results")
#     return results

# if __name__ == "__main__":
#     query = "Skills of Arun"
#     results = query_faiss(query)
#     for result in results:
#         print(f"Profile: {result['profile_id']}, Sentence: {result['sentence']}, Distance: {result['distance']}")


#  working perfect but without query ui
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

       