# import json
# import sys
# import numpy as np
# from openai import OpenAI
# from dotenv import load_dotenv
# import os
# import psycopg2
# from psycopg2.extras import RealDictCursor

# # Load environment variables
# load_dotenv()
# OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# # Database configuration
# DB_CONFIG = {
#     'dbname': os.getenv('DB_NAME', 'profiledb'),
#     'user': os.getenv('DB_USER', 'profile'),
#     'password': os.getenv('DB_PASSWORD', 'profileUYh$13#'),
#     'host': os.getenv('DB_HOST', '122.176.158.168'),
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

# def get_embedding(query):
#     try:
#         response = client.embeddings.create(
#             input=query,
#             model='text-embedding-ada-002'
#         )
#         return np.array(response.data[0].embedding)
#     except Exception as e:
#         print(f"Error generating query embedding: {e}")
#         return None

# def cosine_similarity(a, b):
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# def get_relevant_chunks(query_embedding, top_k=5):
#     conn = get_db_connection()
#     if not conn:
#         return []
#     try:
#         cursor = conn.cursor(cursor_factory=RealDictCursor)
#         cursor.execute('SELECT profile_id, chunk, embedding FROM embeddings')
#         rows = cursor.fetchall()
#         cursor.close()
#         conn.close()

#         similarities = []
#         for row in rows:
#             embedding = np.array(json.loads(row['embedding']))
#             similarity = cosine_similarity(query_embedding, embedding)
#             similarities.append({
#                 'profile_id': row['profile_id'],
#                 'chunk': row['chunk'],
#                 'similarity': similarity
#             })

#         # Sort by similarity and take top_k
#         similarities.sort(key=lambda x: x['similarity'], reverse=True)
#         return similarities[:top_k]
#     except Exception as e:
#         print(f"Error retrieving chunks: {e}")
#         return []

# def query_llm(query, context_chunks):
#     context = '\n'.join(chunk['chunk'] for chunk in context_chunks)
#     prompt = f"""
#     You are a helpful assistant answering questions based on the content of uploaded PDFs.
#     The following is the relevant content from the PDFs:
    
#     {context}
    
#     Question: {query}
    
#     Provide a concise answer based only on the provided content. For each piece of information, include the profile ID it pertains to. If the query asks for information about all profiles, list the relevant information for each profile separately. Return the answer in a structured format where each result includes:
#     - profile_id: The UUID of the profile
#     - sentence: The relevant information or answer
#     - distance: The similarity score (use the provided similarity value)
    
#     Example:
#     [
#       {"profile_id": "uuid1", "sentence": "Skills: React, Node", "distance": 0.95},
#       {"profile_id": "uuid1", "sentence": "Skills: CSS, Bootstrap", "distance": 0.90}
#     ]
#     """
#     try:
#         response = client.chat.completions.create(
#             model='gpt-4o-mini',
#             messages=[
#                 {'role': 'system', 'content': prompt}
#             ],
#             max_tokens=500
#         )
#         # Parse the response (assuming LLM returns JSON-like text)
#         answer = response.choices[0].message.content
#         # Clean up the response (remove code fences if present)
#         answer = answer.strip().replace('```json', '').replace('```', '')
#         results = json.loads(answer)
#         # Add similarity scores from context_chunks
#         for i, result in enumerate(results):
#             result['distance'] = context_chunks[i]['similarity'] if i < len(context_chunks) else 0.0
#         return results
#     except Exception as e:
#         print(f"Error querying LLM: {e}")
#         return []

# if __name__ == '__main__':
#     if len(sys.argv) < 2:
#         print('Usage: python query_openai.py <query>')
#         sys.exit(1)
#     query = sys.argv[1]

#     # Generate query embedding
#     query_embedding = get_embedding(query)
#     if query_embedding is None:
#         print('Failed to generate query embedding')
#         sys.exit(1)

#     # Get relevant chunks
#     context_chunks = get_relevant_chunks(query_embedding)
#     if not context_chunks:
#         print('No relevant chunks found')
#         sys.exit(1)

#     # Query LLM
#     results = query_llm(query, context_chunks)
#     print(json.dumps(results, indent=2))



# import sys
# import json
# import os
# import psycopg2
# import numpy as np
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

# def cosine_similarity(a, b):
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# def query_llm(prompt):
#     try:
#         response = client.chat.completions.create(
#             model='gpt-4o-mini',
#             messages=[{'role': 'system', 'content': prompt}],
#             max_tokens=500
#         )
#         return response.choices[0].message.content
#     except Exception as e:
#         print(f"LLM error: {e}", file=sys.stderr)
#         raise

# def main(query):
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         query_embedding = get_embedding(query)
#         cursor.execute("SELECT profile_id, chunk, embedding FROM embeddings")
#         rows = cursor.fetchall()

#         similarities = []
#         for row in rows:
#             profile_id, chunk, embedding = row
#             # embedding is already a Python list (JSONB)
#             if not isinstance(embedding, list):
#                 embedding = json.loads(embedding)
#             similarity = cosine_similarity(query_embedding, embedding)
#             similarities.append((profile_id, chunk, similarity))

#         similarities.sort(key=lambda x: x[2], reverse=True)
#         top_chunks = similarities[:5]

#         if not top_chunks:
#             print(json.dumps([]))
#             return

#         prompt = f"Answer the query '{query}' based on the following text chunks:\n"
#         for i, (_, chunk, _) in enumerate(top_chunks):
#             prompt += f"Chunk {i+1}: {chunk}\n"
#         prompt += "Return results as a JSON array of objects with profile_id, sentence, and distance."

#         llm_response = query_llm(prompt)
#         results = json.loads(llm_response)

#         for i, result in enumerate(results):
#             for profile_id, _, similarity in top_chunks:
#                 if profile_id == result['profile_id']:
#                     result['distance'] = round(float(similarity), 2)
#                     break

#         print(json.dumps(results))
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) < 2:
#         print("Error: Query argument required", file=sys.stderr)
#         sys.exit(1)
#     query = sys.argv[1]
#     main(query)



# working perfectly before normal response
# import sys
# import json
# import os
# import psycopg2
# import numpy as np
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

# def cosine_similarity(a, b):
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# def query_llm(prompt):
#     try:
#         response = client.chat.completions.create(
#             model='gpt-4o-mini',
#             messages=[
#                 {'role': 'system', 'content': 'You are a helpful assistant that returns JSON responses.'},
#                 {'role': 'user', 'content': prompt}
#             ],
#             max_tokens=500
#         )
#         content = response.choices[0].message.content.strip()
#         print(f"LLM response: {content}", file=sys.stderr)  # Debug log
#         return content
#     except Exception as e:
#         print(f"LLM error: {e}", file=sys.stderr)
#         raise

# def main(query):
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         query_embedding = get_embedding(query)
#         cursor.execute("SELECT profile_id, chunk, embedding FROM embeddings")
#         rows = cursor.fetchall()
#         print(f"Retrieved {len(rows)} embeddings", file=sys.stderr)  # Debug log

#         similarities = []
#         for row in rows:
#             profile_id, chunk, embedding = row
#             if not isinstance(embedding, list):
#                 embedding = json.loads(embedding)
#             similarity = cosine_similarity(query_embedding, embedding)
#             similarities.append((profile_id, chunk, similarity))

#         similarities.sort(key=lambda x: x[2], reverse=True)
#         top_chunks = similarities[:5]
#         print(f"Top {len(top_chunks)} chunks selected", file=sys.stderr)  # Debug log

#         if not top_chunks:
#             print(json.dumps([]))
#             return

#         prompt = (
#             f"Answer the query '{query}' based on the following text chunks. "
#             f"Return a JSON array of objects with keys 'profile_id', 'sentence', and 'distance'. "
#             f"Ensure the response is valid JSON.\n"
#         )
#         for i, (_, chunk, _) in enumerate(top_chunks):
#             prompt += f"Chunk {i+1}: {chunk}\n"
#         print(f"Prompt: {prompt}", file=sys.stderr)  # Debug log

#         llm_response = query_llm(prompt)
#         try:
#             results = json.loads(llm_response)
#             if not isinstance(results, list):
#                 raise ValueError("LLM response must be a JSON array")
#         except json.JSONDecodeError as e:
#             print(f"JSON parse error: {e}, LLM response: {llm_response}", file=sys.stderr)
#             results = []  # Fallback to empty results

#         for i, result in enumerate(results):
#             for profile_id, _, similarity in top_chunks:
#                 if profile_id == result.get('profile_id'):
#                     result['distance'] = round(float(similarity), 2)
#                     break

#         print(json.dumps(results))
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) < 2:
#         print("Error: Query argument required", file=sys.stderr)
#         sys.exit(1)
#     query = sys.argv[1]
#     main(query)


# import sys
# import os
# import psycopg2
# import numpy as np
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

# def cosine_similarity(a, b):
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# def query_llm(prompt):
#     try:
#         response = client.chat.completions.create(
#             model='gpt-4o-mini',
#             messages=[
#                 {'role': 'system', 'content': 'You are a helpful assistant that returns concise natural language answers.'},
#                 {'role': 'user', 'content': prompt}
#             ],
#             max_tokens=100
#         )
#         content = response.choices[0].message.content.strip()
#         print(f"LLM response: {content}", file=sys.stderr)
#         return content
#     except Exception as e:
#         print(f"LLM error: {e}", file=sys.stderr)
#         raise

# def main(query):
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         query_embedding = get_embedding(query)
#         cursor.execute("SELECT profile_id, chunk, embedding FROM embeddings")
#         rows = cursor.fetchall()
#         print(f"Retrieved {len(rows)} embeddings", file=sys.stderr)

#         similarities = []
#         for row in rows:
#             profile_id, chunk, embedding = row
#             if not isinstance(embedding, list):
#                 import json
#                 embedding = json.loads(embedding)
#             similarity = cosine_similarity(query_embedding, embedding)
#             similarities.append((profile_id, chunk, similarity))
#             print(f"Profile {profile_id}: Similarity {similarity:.4f}", file=sys.stderr)

#         similarities.sort(key=lambda x: x[2], reverse=True)
#         top_chunks = similarities[:5]
#         print(f"Top {len(top_chunks)} chunks selected", file=sys.stderr)

#         if not top_chunks:
#             print("No relevant information found.")
#             return

#         prompt = (
#             f"Answer the query '{query}' based on the following text chunks in a concise natural language sentence. "
#             f"Do not include profile IDs or similarity scores.\n"
#         )
#         for i, (_, chunk, _) in enumerate(top_chunks):
#             prompt += f"Chunk {i+1}: {chunk}\n"
#         print(f"Prompt: {prompt}", file=sys.stderr)

#         response = query_llm(prompt)
#         print(response)
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) < 2:
#         print("Error: Query argument required", file=sys.stderr)
#         sys.exit(1)
#     query = sys.argv[1]
#     main(query)


# working but giving arun skill also when ayush
# import sys
# import os
# import psycopg2
# import numpy as np
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

# def cosine_similarity(a, b):
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# def query_llm(prompt):
#     try:
#         response = client.chat.completions.create(
#             model='gpt-4o-mini',
#             messages=[
#                 {'role': 'system', 'content': 'You are a helpful assistant that returns concise natural language answers. For queries asking for all skills, combine skills from all provided chunks into a single list.'},
#                 {'role': 'user', 'content': prompt}
#             ],
#             max_tokens=150
#         )
#         content = response.choices[0].message.content.strip()
#         print(f"LLM response: {content}", file=sys.stderr)
#         return content
#     except Exception as e:
#         print(f"LLM error: {e}", file=sys.stderr)
#         raise

# def main(query):
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         query_embedding = get_embedding(query)
#         cursor.execute("SELECT profile_id, chunk, embedding FROM embeddings")
#         rows = cursor.fetchall()
#         print(f"Retrieved {len(rows)} embeddings", file=sys.stderr)

#         similarities = []
#         for row in rows:
#             profile_id, chunk, embedding = row
#             if not isinstance(embedding, list):
#                 import json
#                 embedding = json.loads(embedding)
#             similarity = cosine_similarity(query_embedding, embedding)
#             similarities.append((profile_id, chunk, similarity))
#             print(f"Profile {profile_id}: Similarity {similarity:.4f}", file=sys.stderr)

#         similarities.sort(key=lambda x: x[2], reverse=True)
#         top_chunks = [s for s in similarities if s[2] > 0.7]
#         print(f"Top {len(top_chunks)} chunks selected", file=sys.stderr)

#         if not top_chunks:
#             print("No relevant information found.")
#             return

#         prompt = (
#             f"Answer the query '{query}' based on the following text chunks in a concise natural language sentence. "
#             f"Do not include profile IDs or similarity scores. "
#             f"If the query asks for all skills, combine skills from all chunks into a single list, avoiding duplicates.\n"
#         )
#         for i, (profile_id, chunk, similarity) in enumerate(top_chunks):
#             prompt += f"Chunk {i+1} (profile_id: {profile_id}, similarity: {similarity:.4f}): {chunk}\n"
#         print(f"Prompt: {prompt}", file=sys.stderr)

#         response = query_llm(prompt)
#         print(response)
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) < 2:
#         print("Error: Query argument required", file=sys.stderr)
#         sys.exit(1)
#     query = sys.argv[1]
#     main(query)


# import sys
# import os
# import psycopg2
# import numpy as np
# from openai import OpenAI
# from dotenv import load_dotenv
# import re

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

# def cosine_similarity(a, b):
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# def query_llm(prompt):
#     try:
#         response = client.chat.completions.create(
#             model='gpt-4o-mini',
#             messages=[
#                 {'role': 'system', 'content': 'You are a helpful assistant that returns concise natural language answers. For queries asking for skills or qualifications, use only the data from the specified profile and combine all relevant information (e.g., skills) from provided chunks into a single list, avoiding duplicates.'},
#                 {'role': 'user', 'content': prompt}
#             ],
#             max_tokens=150
#         )
#         content = response.choices[0].message.content.strip()
#         print(f"LLM response: {content}", file=sys.stderr)
#         return content
#     except Exception as e:
#         print(f"LLM error: {e}", file=sys.stderr)
#         raise

# def get_profile_id(query, cursor):
#     # Extract profile name from query (e.g., "Ayush" from "What are skills of Ayush")
#     match = re.search(r'\bof\s+(\w+)\b', query, re.IGNORECASE)
#     if not match:
#         print("No profile name found in query", file=sys.stderr)
#         return None
#     profile_name = match.group(1)
#     print(f"Extracted profile name: {profile_name}", file=sys.stderr)
#     cursor.execute("SELECT id FROM profiles WHERE name = %s", [profile_name])
#     result = cursor.fetchone()
#     if result:
#         print(f"Found profile_id: {result[0]} for name: {profile_name}", file=sys.stderr)
#         return result[0]
#     print(f"No profile found for name: {profile_name}", file=sys.stderr)
#     return None

# def main(query):
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         # Get profile_id from query
#         profile_id = get_profile_id(query, cursor)
#         if not profile_id:
#             print("No relevant profile found.", file=sys.stderr)
#             print("No relevant profile found.")
#             return

#         query_embedding = get_embedding(query)
#         # Fetch only chunks for the specific profile_id
#         cursor.execute(
#             "SELECT profile_id, chunk, embedding FROM embeddings WHERE profile_id = %s",
#             [profile_id]
#         )
#         rows = cursor.fetchall()
#         print(f"Retrieved {len(rows)} embeddings for profile_id: {profile_id}", file=sys.stderr)

#         similarities = []
#         for row in rows:
#             profile_id, chunk, embedding = row
#             if not isinstance(embedding, list):
#                 import json
#                 embedding = json.loads(embedding)
#             similarity = cosine_similarity(query_embedding, embedding)
#             similarities.append((profile_id, chunk, similarity))
#             print(f"Profile {profile_id}: Similarity {similarity:.4f}", file=sys.stderr)

#         similarities.sort(key=lambda x: x[2], reverse=True)
#         top_chunks = [s for s in similarities if s[2] > 0.7]
#         print(f"Top {len(top_chunks)} chunks selected", file=sys.stderr)

#         if not top_chunks:
#             print("No relevant information found for the profile.")
#             return

#         prompt = (
#             f"Answer the query '{query}' based on the following text chunks for the profile named '{top_chunks[0][1].split('Name: ')[1].split('\n')[0] if 'Name: ' in top_chunks[0][1] else 'unknown'}'. "
#             f"Use only the provided chunks and combine all relevant information (e.g., skills, qualifications) into a concise natural language sentence. "
#             f"Do not include profile IDs, similarity scores, or data from other profiles.\n"
#         )
#         for i, (profile_id, chunk, similarity) in enumerate(top_chunks):
#             prompt += f"Chunk {i+1} (similarity: {similarity:.4f}): {chunk}\n"
#         print(f"Prompt: {prompt}", file=sys.stderr)

#         response = query_llm(prompt)
#         print(response)
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) < 2:
#         print("Error: Query argument required", file=sys.stderr)
#         sys.exit(1)
#     query = sys.argv[1]
#     main(query)


# working might for single
# import sys
# import os
# import psycopg2
# import numpy as np
# from openai import OpenAI
# from dotenv import load_dotenv
# import re

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

# def cosine_similarity(a, b):
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# def query_llm(prompt):
#     try:
#         response = client.chat.completions.create(
#             model='gpt-4o-mini',
#             messages=[
#                 {'role': 'system', 'content': 'You are a helpful assistant that returns concise natural language answers. For queries asking for skills or qualifications, use only the data from the specified profile(s) and combine all relevant information (e.g., skills) from provided chunks into a single list, avoiding duplicates.'},
#                 {'role': 'user', 'content': prompt}
#             ],
#             max_tokens=200
#         )
#         content = response.choices[0].message.content.strip()
#         print(f"LLM response: {content}", file=sys.stderr)
#         return content
#     except Exception as e:
#         print(f"LLM error: {e}", file=sys.stderr)
#         raise

# def get_profile_ids(query, cursor):
#     # Extract profile names from query (e.g., "Amit and Arun" or "Ayush")
#     # Match names after "of" until end or conjunctions like "and"
#     pattern = r'\bof\s+((?:\w+(?:\s+and\s+\w+)*))\b'
#     match = re.search(pattern, query, re.IGNORECASE)
#     if not match:
#         print("No profile names found in query", file=sys.stderr)
#         return []
#     profile_names_str = match.group(1)
#     # Split names by "and" and strip whitespace
#     profile_names = [name.strip() for name in profile_names_str.split(' and ')]
#     print(f"Extracted profile names: {profile_names}", file=sys.stderr)

#     profile_ids = []
#     for name in profile_names:
#         cursor.execute("SELECT id FROM profiles WHERE name = %s", [name])
#         result = cursor.fetchone()
#         if result:
#             print(f"Found profile_id: {result[0]} for name: {name}", file=sys.stderr)
#             profile_ids.append((name, result[0]))
#         else:
#             print(f"No profile found for name: {name}", file=sys.stderr)
#     return profile_ids

# def main(query):
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         # Get profile_id(s) from query
#         profile_ids = get_profile_ids(query, cursor)
#         if not profile_ids:
#             print("No relevant profiles found.", file=sys.stderr)
#             print("No relevant profiles found.")
#             return

#         query_embedding = get_embedding(query)
#         responses = []
#         for profile_name, profile_id in profile_ids:
#             # Fetch chunks for this profile_id
#             cursor.execute(
#                 "SELECT profile_id, chunk, embedding FROM embeddings WHERE profile_id = %s",
#                 [profile_id]
#             )
#             rows = cursor.fetchall()
#             print(f"Retrieved {len(rows)} embeddings for profile_id: {profile_id} (name: {profile_name})", file=sys.stderr)

#             similarities = []
#             for row in rows:
#                 pid, chunk, embedding = row
#                 if not isinstance(embedding, list):
#                     import json
#                     embedding = json.loads(embedding)
#                 similarity = cosine_similarity(query_embedding, embedding)
#                 similarities.append((pid, chunk, similarity))
#                 print(f"Profile {pid}: Similarity {similarity:.4f}", file=sys.stderr)

#             similarities.sort(key=lambda x: x[2], reverse=True)
#             top_chunks = [s for s in similarities if s[2] > 0.7]
#             print(f"Top {len(top_chunks)} chunks selected for {profile_name}", file=sys.stderr)

#             if top_chunks:
#                 prompt = (
#                     f"Answer the query '{query}' for the profile named '{profile_name}'. "
#                     f"Use only the following text chunks and combine all relevant information (e.g., skills, qualifications) into a concise natural language sentence. "
#                     f"Do not include profile IDs, similarity scores, or data from other profiles.\n"
#                 )
#                 for i, (pid, chunk, similarity) in enumerate(top_chunks):
#                     prompt += f"Chunk {i+1} (similarity: {similarity:.4f}): {chunk}\n"
#                 print(f"Prompt for {profile_name}: {prompt}", file=sys.stderr)
#                 response = query_llm(prompt)
#                 responses.append(response)

#         if not responses:
#             print("No relevant information found for any profiles.")
#             return

#         # Combine responses
#         final_response = " ".join(responses)
#         print(final_response)
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) < 2:
#         print("Error: Query argument required", file=sys.stderr)
#         sys.exit(1)
#     query = sys.argv[1]
#     main(query)





# import sys
# import os
# import psycopg2
# import numpy as np
# from openai import OpenAI
# from dotenv import load_dotenv
# import re

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

# def cosine_similarity(a, b):
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# def query_llm(prompt):
#     try:
#         response = client.chat.completions.create(
#             model='gpt-4o-mini',
#             messages=[
#                 {'role': 'system', 'content': 'You are a helpful assistant that returns concise natural language answers. For queries asking for skills or qualifications, use only the data from the specified profile and combine all relevant information (e.g., skills) from provided chunks into a single list, avoiding duplicates. For multiple profiles, provide a clear combined response.'},
#                 {'role': 'user', 'content': prompt}
#             ],
#             max_tokens=200
#         )
#         content = response.choices[0].message.content.strip()
#         print(f"LLM response: {content}", file=sys.stderr)
#         return content
#     except Exception as e:
#         print(f"LLM error: {e}", file=sys.stderr)
#         raise

# def get_profile_ids(query, cursor):
#     # Extract profile names (e.g., "Amit and Arun" or "Ayush")
#     query_lower = query.lower()
#     # Match names after "of" or in a list (e.g., "Amit and Arun")
#     match = re.search(r'\bof\s+(.+?)(?:\s*\?|$)', query_lower)
#     if not match:
#         print("No profile names found in query", file=sys.stderr)
#         return []
#     names_str = match.group(1)
#     # Split names by "and", ",", or "or"
#     names = re.split(r'\s*(?:and|or|,)\s*', names_str)
#     names = [name.strip() for name in names if name.strip()]
#     print(f"Extracted profile names: {names}", file=sys.stderr)

#     profile_ids = []
#     for name in names:
#         cursor.execute("SELECT id FROM profiles WHERE lower(name) = %s", [name])
#         result = cursor.fetchone()
#         if result:
#             print(f"Found profile_id: {result[0]} for name: {name}", file=sys.stderr)
#             profile_ids.append((name, result[0]))
#         else:
#             print(f"No profile found for name: {name}", file=sys.stderr)
#             profile_ids.append((name, None))
#     return profile_ids

# def main(query):
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         # Get profile IDs
#         profile_ids = get_profile_ids(query, cursor)
#         if not profile_ids:
#             print("No relevant profiles found.", file=sys.stderr)
#             print("No relevant profiles found.")
#             return

#         query_embedding = get_embedding(query)
#         results = []
#         for name, profile_id in profile_ids:
#             if not profile_id:
#                 results.append(f"{name} has no relevant profile found.")
#                 continue

#             # Fetch chunks for this profile_id
#             cursor.execute(
#                 "SELECT profile_id, chunk, embedding FROM embeddings WHERE profile_id = %s",
#                 [profile_id]
#             )
#             rows = cursor.fetchall()
#             print(f"Retrieved {len(rows)} embeddings for profile_id: {profile_id}", file=sys.stderr)

#             similarities = []
#             for row in rows:
#                 row_profile_id, chunk, embedding = row
#                 if not isinstance(embedding, list):
#                     import json
#                     embedding = json.loads(embedding)
#                 similarity = cosine_similarity(query_embedding, embedding)
#                 similarities.append((row_profile_id, chunk, similarity))
#                 print(f"Profile {row_profile_id}: Similarity {similarity:.4f}", file=sys.stderr)

#             similarities.sort(key=lambda x: x[2], reverse=True)
#             top_chunks = [s for s in similarities if s[2] > 0.7]
#             print(f"Top {len(top_chunks)} chunks selected for {name}", file=sys.stderr)

#             if not top_chunks:
#                 results.append(f"No relevant information found for {name}.")
#                 continue

#             prompt = (
#                 f"Answer the query '{query}' for the profile named '{name}' based on the following text chunks. "
#                 f"Use only these chunks and combine all relevant information (e.g., skills, qualifications) into a concise natural language sentence. "
#                 f"Do not include profile IDs, similarity scores, or data from other profiles.\n"
#             )
#             for i, (_, chunk, similarity) in enumerate(top_chunks):
#                 prompt += f"Chunk {i+1} (similarity: {similarity:.4f}): {chunk}\n"
#             print(f"Prompt for {name}: {prompt}", file=sys.stderr)

#             response = query_llm(prompt)
#             results.append(response)

#         # Combine results
#         if not results:
#             print("No relevant information found for any profile.")
#             return
#         combined_response = ", while ".join(results)
#         print(combined_response)
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) < 2:
#         print("Error: Query argument required", file=sys.stderr)
#         sys.exit(1)
#     query = sys.argv[1]
#     main(query)





# import sys
# import os
# import psycopg2
# import numpy as np
# from openai import OpenAI
# from dotenv import load_dotenv
# import re
# import json

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

# def cosine_similarity(a, b):
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# def query_llm(prompt, max_tokens=200):
#     try:
#         response = client.chat.completions.create(
#             model='gpt-4o-mini',
#             messages=[
#                 {'role': 'system', 'content': 'You are a helpful assistant that returns concise, natural language answers. For queries about skills or qualifications, use only the provided chunks for the specified profile(s). Combine all relevant information (e.g., skills) into a single list, avoiding duplicates. For multiple profiles, provide a clear, combined response. If a profile has no data, state it clearly.'},
#                 {'role': 'user', 'content': prompt}
#             ],
#             max_tokens=max_tokens
#         )
#         content = response.choices[0].message.content.strip()
#         print(f"LLM response: {content}", file=sys.stderr)
#         return content
#     except Exception as e:
#         print(f"LLM error: {e}", file=sys.stderr)
#         raise

# def extract_profile_names(query):
#     # Use LLM to interpret query intent and extract profile names
#     intent_prompt = (
#         f"Analyze the query: '{query}'. Identify the profile names or if it refers to 'all profiles'. "
#         f"Return a JSON object with either 'names': ['name1', 'name2', ...] or 'all_profiles': true."
#     )
#     intent_response = query_llm(intent_prompt, max_tokens=100)
#     try:
#         intent_data = json.loads(intent_response)
#         return intent_data
#     except json.JSONDecodeError:
#         print(f"Failed to parse LLM intent response: {intent_response}", file=sys.stderr)
#         # Fallback to regex
#         query_lower = query.lower()
#         if 'all profiles' in query_lower:
#             return {'all_profiles': True}
#         match = re.search(r'\b(of|for|does)\s+(.+?)(?:\s*\?|$)', query_lower)
#         if not match:
#             print("No profile names found in query", file=sys.stderr)
#             return {'names': []}
#         names_str = match.group(2)
#         names = re.split(r'\s*(?:and|or|,)\s*', names_str)
#         names = [name.strip() for name in names if name.strip()]
#         print(f"Fallback extracted profile names: {names}", file=sys.stderr)
#         return {'names': names}

# def get_profile_ids(names, cursor, all_profiles=False):
#     profile_ids = []
#     if all_profiles:
#         cursor.execute("SELECT id, name FROM profiles")
#         rows = cursor.fetchall()
#         for row in rows:
#             profile_ids.append((row[1], row[0]))
#             print(f"Found profile_id: {row[0]} for name: {row[1]}", file=sys.stderr)
#     else:
#         for name in names:
#             cursor.execute("SELECT id, name FROM profiles WHERE lower(name) = %s", [name.lower()])
#             result = cursor.fetchone()
#             if result:
#                 print(f"Found profile_id: {result[0]} for name: {name}", file=sys.stderr)
#                 profile_ids.append((result[1], result[0]))
#             else:
#                 print(f"No profile found for name: {name}", file=sys.stderr)
#                 profile_ids.append((name, None))
#     return profile_ids

# def main(query):
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         # Extract profile names or all_profiles
#         intent_data = extract_profile_names(query)
#         names = intent_data.get('names', [])
#         all_profiles = intent_data.get('all_profiles', False)
#         print(f"Intent data: {intent_data}", file=sys.stderr)

#         # Get profile IDs
#         profile_ids = get_profile_ids(names, cursor, all_profiles)
#         if not profile_ids:
#             print("No relevant profiles found.", file=sys.stderr)
#             print("No relevant profiles found.")
#             return

#         query_embedding = get_embedding(query)
#         results = []
#         for name, profile_id in profile_ids:
#             if not profile_id:
#                 results.append(f"{name.capitalize()} has no relevant profile found.")
#                 continue

#             # Fetch chunks for this profile_id
#             cursor.execute(
#                 "SELECT profile_id, chunk, embedding FROM embeddings WHERE profile_id = %s",
#                 [profile_id]
#             )
#             rows = cursor.fetchall()
#             print(f"Retrieved {len(rows)} embeddings for profile_id: {profile_id}", file=sys.stderr)

#             similarities = []
#             for row in rows:
#                 row_profile_id, chunk, embedding = row
#                 if not isinstance(embedding, list):
#                     embedding = json.loads(embedding)
#                 similarity = cosine_similarity(query_embedding, embedding)
#                 similarities.append((row_profile_id, chunk, similarity))
#                 print(f"Profile {row_profile_id}: Similarity {similarity:.4f}", file=sys.stderr)

#             similarities.sort(key=lambda x: x[2], reverse=True)
#             top_chunks = [s for s in similarities if s[2] > 0.7]
#             print(f"Top {len(top_chunks)} chunks selected for {name}", file=sys.stderr)

#             if not top_chunks:
#                 results.append(f"No relevant information found for {name.capitalize()}.")
#                 continue

#             prompt = (
#                 f"Answer the query '{query}' for the profile named '{name}'. "
#                 f"Use only these chunks and combine all relevant information (e.g., skills, qualifications) into a concise natural language sentence. "
#                 f"Do not include profile IDs, similarity scores, or data from other profiles.\n"
#             )
#             for i, (_, chunk, similarity) in enumerate(top_chunks):
#                 prompt += f"Chunk {i+1} (similarity: {similarity:.4f}): {chunk}\n"
#             print(f"Prompt for {name}: {prompt}", file=sys.stderr)

#             response = query_llm(prompt)
#             results.append(response)

#         # Combine results
#         if not results:
#             print("No relevant information found for any profile.")
#             return
#         combined_response = ", while ".join(results)
#         print(combined_response)
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) < 2:
#         print("Error: Query argument required", file=sys.stderr)
#         sys.exit(1)
#     query = sys.argv[1]
#     main(query)



# may be this 
# import sys
# import os
# import psycopg2
# import numpy as np
# from openai import OpenAI
# from dotenv import load_dotenv
# import json
# import re

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

# def cosine_similarity(a, b):
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# def query_llm(prompt, max_tokens=200):
#     try:
#         response = client.chat.completions.create(
#             model='gpt-4o-mini',
#             messages=[
#                 {'role': 'system', 'content': 'You are a precise assistant that returns concise, natural language answers or structured JSON as requested. For profile queries, use only provided data, combining relevant information (e.g., skills) into a single list without duplicates. For multiple profiles, format responses fluently, avoiding repetitive connectors like "while." For JSON responses, return clean JSON without markdown.'},
#                 {'role': 'user', 'content': prompt}
#             ],
#             max_tokens=max_tokens
#         )
#         content = response.choices[0].message.content.strip()
#         print(f"LLM response: {content}", file=sys.stderr)
#         return content
#     except Exception as e:
#         print(f"LLM error: {e}", file=sys.stderr)
#         raise

# def clean_json_response(response):
#     # Remove markdown code blocks and extra whitespace
#     cleaned = re.sub(r'```json\s*|\s*```', '', response).strip()
#     try:
#         return json.loads(cleaned)
#     except json.JSONDecodeError as e:
#         print(f"JSON parse error: {e}, response: {cleaned}", file=sys.stderr)
#         return None

# def extract_intent(query):
#     intent_prompt = (
#         f"Analyze the query: '{query}'. Determine the intent and identify profile names or 'all profiles'. "
#         f"Return clean JSON (no markdown) with: "
#         f"- 'intent': 'skills', 'qualifications', 'skills_and_qualifications', 'names', or 'other' "
#         f"- 'profiles': ['name1', 'name2', ...] or 'all' "
#         f"Consider 'all', 'all profiles', or similar as 'all'. "
#         f"Examples: "
#         f"- 'What all skills does Arvind have?' → {{'intent': 'skills', 'profiles': ['Arvind']}} "
#         f"- 'Give me all skills?' → {{'intent': 'skills', 'profiles': 'all'}} "
#         f"- 'Give me names of all profiles' → {{'intent': 'names', 'profiles': 'all'}} "
#         f"- 'What are skills of Arvind and Ayush?' → {{'intent': 'skills', 'profiles': ['Arvind', 'Ayush']}} "
#     )
#     intent_response = query_llm(intent_prompt, max_tokens=100)
#     intent_data = clean_json_response(intent_response)
#     if intent_data:
#         return intent_data

#     # Fallback: regex for basic parsing
#     print("Falling back to regex parsing", file=sys.stderr)
#     query_lower = query.lower()
#     intent = 'other'
#     profiles = []
#     if 'skill' in query_lower:
#         intent = 'skills'
#     elif 'qualification' in query_lower:
#         intent = 'skills_and_qualifications' if 'skill' in query_lower else 'qualifications'
#     elif 'name' in query_lower:
#         intent = 'names'

#     if 'all profiles' in query_lower or 'all' in query_lower:
#         profiles = 'all'
#     else:
#         match = re.search(r'\b(of|for|does)\s+(.+?)(?:\s*\?|$)', query_lower)
#         if match:
#             names_str = match.group(2)
#             profiles = re.split(r'\s*(?:and|or|,)\s*', names_str)
#             profiles = [name.strip() for name in profiles if name.strip()]
#     intent_data = {'intent': intent, 'profiles': profiles}
#     print(f"Fallback intent data: {intent_data}", file=sys.stderr)
#     return intent_data

# def get_profile_ids(profiles, cursor):
#     profile_ids = []
#     if profiles == 'all':
#         cursor.execute("SELECT id, name FROM profiles ORDER BY name")
#         rows = cursor.fetchall()
#         for row in rows:
#             profile_ids.append((row[1], row[0]))
#             print(f"Found profile_id: {row[0]} for name: {row[1]}", file=sys.stderr)
#     else:
#         for name in profiles:
#             cursor.execute("SELECT id, name FROM profiles WHERE lower(name) = %s", [name.lower()])
#             result = cursor.fetchone()
#             if result:
#                 profile_ids.append((result[1], result[0]))
#                 print(f"Found profile_id: {result[0]} for name: {name}", file=sys.stderr)
#             else:
#                 profile_ids.append((name, None))
#                 print(f"No profile found for name: {name}", file=sys.stderr)
#     return profile_ids

# def format_response(results, intent):
#     if not results:
#         return "No relevant information found for any profile."
#     if intent == 'names':
#         names = [r for r in results if not r.startswith("No ")]
#         if not names:
#             return "No profiles found."
#         return ", ".join(names)
#     prompt = (
#         f"Format these results into a natural, fluent response without repetitive connectors like 'while':\n"
#         f"{json.dumps(results)}\n"
#         f"Use a single sentence or paragraph that flows naturally, e.g., "
#         f"'Arun has skills in CSS and React, Arvind has skills in Putty, Ayush has skills in Machine Learning, and no skills are available for Bipin and Chhavi.'"
#     )
#     return query_llm(prompt, max_tokens=300)

# def main(query):
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         # Extract intent and profiles
#         intent_data = extract_intent(query)
#         intent = intent_data.get('intent', 'other')
#         profiles = intent_data.get('profiles', [])
#         print(f"Processed intent data: {intent_data}", file=sys.stderr)

#         # Get profile IDs
#         profile_ids = get_profile_ids(profiles, cursor)
#         if not profile_ids:
#             print("No relevant profiles found.", file=sys.stderr)
#             print("No relevant profiles found.")
#             return

#         results = []
#         if intent == 'names':
#             for name, profile_id in profile_ids:
#                 if profile_id:
#                     results.append(name.capitalize())
#                 else:
#                     results.append(f"No relevant information found for {name.capitalize()}.")
#             print(format_response(results, intent))
#             return

#         query_embedding = get_embedding(query)
#         for name, profile_id in profile_ids:
#             if not profile_id:
#                 results.append(f"No relevant information found for {name.capitalize()}.")
#                 continue

#             # Fetch chunks
#             cursor.execute(
#                 "SELECT profile_id, chunk, embedding FROM embeddings WHERE profile_id = %s",
#                 [profile_id]
#             )
#             rows = cursor.fetchall()
#             print(f"Retrieved {len(rows)} embeddings for profile_id: {profile_id}", file=sys.stderr)

#             similarities = []
#             for row in rows:
#                 row_profile_id, chunk, embedding = row
#                 if not isinstance(embedding, list):
#                     embedding = json.loads(embedding)
#                 similarity = cosine_similarity(query_embedding, embedding)
#                 similarities.append((row_profile_id, chunk, similarity))
#                 print(f"Profile {row_profile_id}: Similarity {similarity:.4f}", file=sys.stderr)

#             similarities.sort(key=lambda x: x[2], reverse=True)
#             top_chunks = [s for s in similarities if s[2] > 0.7]
#             print(f"Top {len(top_chunks)} chunks selected for {name}", file=sys.stderr)

#             if not top_chunks:
#                 results.append(f"No relevant information found for {name.capitalize()}.")
#                 continue

#             prompt = (
#                 f"Answer the query '{query}' for the profile named '{name}'. "
#                 f"Use only these chunks and combine all relevant information (e.g., skills, qualifications) into a concise natural language sentence. "
#                 f"Focus on the requested intent ({intent}). Do not include profile IDs or similarity scores.\n"
#             )
#             for i, (_, chunk, similarity) in enumerate(top_chunks):
#                 prompt += f"Chunk {i+1} (similarity: {similarity:.4f}): {chunk}\n"
#             print(f"Prompt for {name}: {prompt}", file=sys.stderr)

#             response = query_llm(prompt)
#             results.append(response)

#         # Format final response
#         print(format_response(results, intent))
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) < 2:
#         print("Error: Query argument required", file=sys.stderr)
#         sys.exit(1)
#     query = sys.argv[1]
#     main(query)



# import sys
# import os
# import psycopg2
# import numpy as np
# from openai import OpenAI
# from dotenv import load_dotenv
# import json
# import re

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

# def cosine_similarity(a, b):
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# def query_llm(prompt, max_tokens=200):
#     try:
#         response = client.chat.completions.create(
#             model='gpt-4o-mini',
#             messages=[
#                 {'role': 'system', 'content': 'You are a precise assistant that returns concise, natural language answers or structured JSON as requested. For profile queries, use only provided data, combining relevant information (e.g., skills) into a single list without duplicates. For multiple profiles, format responses fluently, avoiding repetitive connectors like "while." For JSON, return clean JSON without markdown.'},
#                 {'role': 'user', 'content': prompt}
#             ],
#             max_tokens=max_tokens
#         )
#         content = response.choices[0].message.content.strip()
#         print(f"LLM response: {content}", file=sys.stderr)
#         return content
#     except Exception as e:
#         print(f"LLM error: {e}", file=sys.stderr)
#         raise

# def clean_json_response(response):
#     cleaned = re.sub(r'```json\s*|\s*```', '', response).strip()
#     try:
#         return json.loads(cleaned)
#     except json.JSONDecodeError as e:
#         print(f"JSON parse error: {e}, response: {cleaned}", file=sys.stderr)
#         return None

# def extract_intent(query):
#     intent_prompt = (
#         f"Analyze the query: '{query}'. Determine the intent and identify profile names or 'all profiles'. "
#         f"Return clean JSON with: "
#         f"- 'intent': 'skills', 'qualifications', 'addresses', 'names', 'count', 'greeting', 'irrelevant', or 'all_data' "
#         f"- 'profiles': ['name1', 'name2', ...] or 'all' "
#         f"Rules: "
#         f"- 'skills': Queries asking for skills (e.g., 'What all skills does Arun have?'). "
#         f"- 'qualifications': Queries asking for degrees or qualifications (e.g., 'What are all qualifications?'). "
#         f"- 'addresses': Queries asking for addresses (e.g., 'Provide address of Arun'). "
#         f"- 'names': Queries asking for profile names (e.g., 'Provide me all names'). "
#         f"- 'count': Queries asking for number of profiles (e.g., 'Total how many profiles do I have?'). "
#         f"- 'greeting': Greetings like 'Hi?' or 'Hello'. "
#         f"- 'irrelevant': Queries unrelated to profiles (e.g., 'Most played game?'). "
#         f"- 'all_data': Generic profile queries (e.g., 'Tell me about all profiles'). "
#         f"- Consider 'all', 'all profiles', or similar as 'all'. "
#         f"Examples: "
#         f"- 'What all skills does Arvind have?' → {{'intent': 'skills', 'profiles': ['Arvind']}} "
#         f"- 'What are all qualifications?' → {{'intent': 'qualifications', 'profiles': 'all'}} "
#         f"- 'Provide address of Arun and Ayush' → {{'intent': 'addresses', 'profiles': ['Arun', 'Ayush']}} "
#         f"- 'Give me number of profiles' → {{'intent': 'count', 'profiles': 'all'}} "
#         f"- 'Hi?' → {{'intent': 'greeting', 'profiles': []}} "
#         f"- 'Most played game?' → {{'intent': 'irrelevant', 'profiles': []}} "
#     )
#     intent_response = query_llm(intent_prompt, max_tokens=100)
#     intent_data = clean_json_response(intent_response)
#     if intent_data:
#         return intent_data

#     # Fallback: regex
#     print("Falling back to regex parsing", file=sys.stderr)
#     query_lower = query.lower()
#     intent = 'all_data'
#     profiles = []
#     if 'skill' in query_lower:
#         intent = 'skills'
#     elif 'qualification' in query_lower or 'degree' in query_lower:
#         intent = 'qualifications'
#     elif 'address' in query_lower:
#         intent = 'addresses'
#     elif 'name' in query_lower:
#         intent = 'names'
#     elif 'how many' in query_lower or 'number of' in query_lower:
#         intent = 'count'
#     elif query_lower.strip() in ['hi', 'hello', 'hi?']:
#         intent = 'greeting'
#     elif not query_lower.strip().endswith('profiles?'):
#         intent = 'irrelevant'

#     if 'all profiles' in query_lower or 'all' in query_lower:
#         profiles = 'all'
#     else:
#         match = re.search(r'\b(of|for|does)\s+(.+?)(?:\s*\?|$)', query_lower)
#         if match:
#             names_str = match.group(2)
#             profiles = re.split(r'\s*(?:and|or|,)\s*', names_str)
#             profiles = [name.strip() for name in profiles if name.strip()]
#     intent_data = {'intent': intent, 'profiles': profiles}
#     print(f"Fallback intent data: {intent_data}", file=sys.stderr)
#     return intent_data

# def get_profile_ids(profiles, cursor):
#     profile_ids = []
#     if profiles == 'all':
#         cursor.execute("SELECT id, name FROM profiles ORDER BY name")
#         rows = cursor.fetchall()
#         for row in rows:
#             profile_ids.append((row[1], row[0]))
#             print(f"Found profile_id: {row[0]} for name: {row[1]}", file=sys.stderr)
#     else:
#         for name in profiles:
#             cursor.execute("SELECT id, name FROM profiles WHERE lower(name) = %s", [name.lower()])
#             result = cursor.fetchone()
#             if result:
#                 profile_ids.append((result[1], result[0]))
#                 print(f"Found profile_id: {result[0]} for name: {name}", file=sys.stderr)
#             else:
#                 profile_ids.append((name, None))
#                 print(f"No profile found for name: {name}", file=sys.stderr)
#     return profile_ids

# def format_response(results, intent):
#     if not results:
#         return "No relevant information found for any profile."
#     if intent == 'names':
#         names = [r for r in results if not r.startswith("No ")]
#         if not names:
#             return "No profiles found."
#         return ", ".join(names)
#     if intent == 'count':
#         count = len([r for r in results if not r.startswith("No ")])
#         names = [r for r in results if not r.startswith("No ")]
#         return f"You have {count} profiles: {', '.join(names)}."
#     if intent == 'greeting':
#         return "Hello! How can I assist you with the profiles?"
#     if intent == 'irrelevant':
#         return "No relevant information is available for this query."
#     prompt = (
#         f"Format these results into a natural, fluent response without repetitive connectors like 'while':\n"
#         f"{json.dumps(results)}\n"
#         f"Use a single sentence or paragraph that flows naturally, e.g., "
#         f"'Arun has skills in CSS and React, Arvind has skills in Putty, and no skills are available for Bipin.' "
#         f"Ensure the response strictly matches the intent '{intent}' (e.g., only qualifications for 'qualifications')."
#     )
#     return query_llm(prompt, max_tokens=300)

# def main(query):
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         # Extract intent and profiles
#         intent_data = extract_intent(query)
#         intent = intent_data.get('intent', 'all_data')
#         profiles = intent_data.get('profiles', [])
#         print(f"Processed intent data: {intent_data}", file=sys.stderr)

#         # Handle greeting or irrelevant queries
#         if intent in ['greeting', 'irrelevant']:
#             print(format_response([], intent))
#             return

#         # Handle count query
#         if intent == 'count':
#             profile_ids = get_profile_ids('all', cursor)
#             results = []
#             for name, profile_id in profile_ids:
#                 if profile_id:
#                     results.append(name.capitalize())
#                 else:
#                     results.append(f"No relevant information found for {name.capitalize()}.")
#             print(format_response(results, intent))
#             return

#         # Get profile IDs
#         profile_ids = get_profile_ids(profiles, cursor)
#         if not profile_ids:
#             print("No relevant profiles found.", file=sys.stderr)
#             print("No relevant profiles found.")
#             return

#         results = []
#         if intent == 'names':
#             for name, profile_id in profile_ids:
#                 if profile_id:
#                     results.append(name.capitalize())
#                 else:
#                     results.append(f"No relevant information found for {name.capitalize()}.")
#             print(format_response(results, intent))
#             return

#         query_embedding = get_embedding(query)
#         for name, profile_id in profile_ids:
#             if not profile_id:
#                 results.append(f"No relevant information found for {name.capitalize()}.")
#                 continue

#             # Fetch chunks
#             cursor.execute(
#                 "SELECT profile_id, chunk, embedding FROM embeddings WHERE profile_id = %s",
#                 [profile_id]
#             )
#             rows = cursor.fetchall()
#             print(f"Retrieved {len(rows)} embeddings for profile_id: {profile_id}", file=sys.stderr)

#             similarities = []
#             for row in rows:
#                 row_profile_id, chunk, embedding = row
#                 if not isinstance(embedding, list):
#                     embedding = json.loads(embedding)
#                 similarity = cosine_similarity(query_embedding, embedding)
#                 similarities.append((row_profile_id, chunk, similarity))
#                 print(f"Profile {row_profile_id}: Similarity {similarity:.4f}", file=sys.stderr)

#             similarities.sort(key=lambda x: x[2], reverse=True)
#             top_chunks = [s for s in similarities if s[2] > 0.7]
#             print(f"Top {len(top_chunks)} chunks selected for {name}", file=sys.stderr)

#             if not top_chunks:
#                 results.append(f"No relevant information found for {name.capitalize()}.")
#                 continue

#             prompt = (
#                 f"Answer the query '{query}' for the profile named '{name}'. "
#                 f"Use only these chunks and combine all relevant information into a concise natural language sentence. "
#                 f"Strictly focus on the requested intent ({intent}): "
#                 f"- 'skills': List only skills. "
#                 f"- 'qualifications': List only qualifications/degrees. "
#                 f"- 'addresses': List only addresses. "
#                 f"- 'all_data': Include all available data (skills, qualifications, addresses). "
#                 f"Do not include profile IDs, similarity scores, or extraneous data.\n"
#             )
#             for i, (_, chunk, similarity) in enumerate(top_chunks):
#                 prompt += f"Chunk {i+1} (similarity: {similarity:.4f}): {chunk}\n"
#             print(f"Prompt for {name}: {prompt}", file=sys.stderr)

#             response = query_llm(prompt)
#             results.append(response)

#         # Format final response
#         print(format_response(results, intent))
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) < 2:
#         print("Error: Query argument required", file=sys.stderr)
#         sys.exit(1)
#     query = sys.argv[1]
#     main(query)




# import sys
# import os
# import psycopg2
# import numpy as np
# from openai import OpenAI
# from dotenv import load_dotenv
# import json
# import re

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

# def cosine_similarity(a, b):
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# def query_llm(prompt, max_tokens=200):
#     try:
#         response = client.chat.completions.create(
#             model='gpt-4o-mini',
#             messages=[
#                 {'role': 'system', 'content': 'You are a precise assistant that returns concise, natural language answers or structured JSON as requested. For profile queries, use only provided data, combining relevant information (e.g., skills) into a single list without duplicates. For multiple profiles, format responses fluently, avoiding repetitive connectors like "while." Use "degree" for qualifications consistently. For JSON, return clean JSON without markdown.'},
#                 {'role': 'user', 'content': prompt}
#             ],
#             max_tokens=max_tokens
#         )
#         content = response.choices[0].message.content.strip()
#         print(f"LLM response: {content}", file=sys.stderr)
#         return content
#     except Exception as e:
#         print(f"LLM error: {e}", file=sys.stderr)
#         raise

# def clean_json_response(response):
#     cleaned = re.sub(r'```json\s*|\s*```', '', response).strip()
#     try:
#         return json.loads(cleaned)
#     except json.JSONDecodeError as e:
#         print(f"JSON parse error: {e}, response: {cleaned}", file=sys.stderr)
#         return None

# def extract_intent(query):
#     intent_prompt = (
#         f"Analyze the query: '{query}'. Determine the intent and identify profile names or 'all profiles'. "
#         f"Return clean JSON with: "
#         f"- 'intent': 'skills', 'qualifications', 'addresses', 'names', 'count', 'greeting', 'irrelevant', or 'all_data' "
#         f"- 'profiles': ['name1', 'name2', ...] or 'all' "
#         f"Rules: "
#         f"- 'skills': Queries asking for skills (e.g., 'What all skills does Arun have?'). "
#         f"- 'qualifications': Queries asking for degrees or qualifications (e.g., 'What are all qualifications?'). "
#         f"- 'addresses': Queries asking for addresses (e.g., 'Provide address of Arun'). "
#         f"- 'names': Queries asking for profile names (e.g., 'Provide me all names'). "
#         f"- 'count': Queries asking for number of profiles (e.g., 'Total how many profiles do I have?'). "
#         f"- 'greeting': Greetings like 'Hi?', 'Hello', 'Hey' (case-insensitive, with or without punctuation). "
#         f"- 'irrelevant': Queries unrelated to profiles (e.g., 'Most played game?'). "
#         f"- 'all_data': Generic profile queries (e.g., 'Tell me about all profiles'). "
#         f"- Consider 'all', 'all profiles', or similar as 'all'. "
#         f"- Handle typos (e.g., 'adres' as 'address'). "
#         f"Examples: "
#         f"- 'What all skills does Arvind have?' → {{'intent': 'skills', 'profiles': ['Arvind']}} "
#         f"- 'What are all Qualifications?' → {{'intent': 'qualifications', 'profiles': 'all'}} "
#         f"- 'Arun's adres is?' → {{'intent': 'addresses', 'profiles': ['Arun']}} "
#         f"- 'Hi?' → {{'intent': 'greeting', 'profiles': []}} "
#         f"- 'Which game do Arun like?' → {{'intent': 'irrelevant', 'profiles': ['Arun']}} "
#     )
#     intent_response = query_llm(intent_prompt, max_tokens=100)
#     intent_data = clean_json_response(intent_response)
#     if intent_data:
#         return intent_data

#     # Fallback: regex
#     print("Falling back to regex parsing", file=sys.stderr)
#     query_lower = query.lower().strip()
#     intent = 'all_data'
#     profiles = []
#     if 'skill' in query_lower:
#         intent = 'skills'
#     elif 'qualification' in query_lower or 'degree' in query_lower:
#         intent = 'qualifications'
#     elif 'address' in query_lower or 'adres' in query_lower:
#         intent = 'addresses'
#     elif 'name' in query_lower:
#         intent = 'names'
#     elif 'how many' in query_lower or 'number of' in query_lower:
#         intent = 'count'
#     elif query_lower in ['hi', 'hi?', 'hello', 'hello?', 'hey', 'hey?']:
#         intent = 'greeting'
#     elif not query_lower.endswith('profiles?'):
#         intent = 'irrelevant'

#     if 'all profiles' in query_lower or 'all' in query_lower:
#         profiles = 'all'
#     else:
#         match = re.search(r'\b(of|for|does)\s+(.+?)(?:\s*\?|$)', query_lower)
#         if match:
#             names_str = match.group(2)
#             profiles = re.split(r'\s*(?:and|or|,)\s*', names_str)
#             profiles = [name.strip() for name in profiles if name.strip()]
#     intent_data = {'intent': intent, 'profiles': profiles}
#     print(f"Fallback intent data: {intent_data}", file=sys.stderr)
#     return intent_data

# def get_profile_ids(profiles, cursor):
#     profile_ids = []
#     if profiles == 'all':
#         cursor.execute("SELECT id, name FROM profiles ORDER BY name")
#         rows = cursor.fetchall()
#         for row in rows:
#             profile_ids.append((row[1], row[0]))
#             print(f"Found profile_id: {row[0]} for name: {row[1]}", file=sys.stderr)
#     else:
#         for name in profiles:
#             cursor.execute("SELECT id, name FROM profiles WHERE lower(name) = %s", [name.lower()])
#             result = cursor.fetchone()
#             if result:
#                 profile_ids.append((result[1], result[0]))
#                 print(f"Found profile_id: {result[0]} for name: {name}", file=sys.stderr)
#             else:
#                 profile_ids.append((name, None))
#                 print(f"No profile found for name: {name}", file=sys.stderr)
#     return profile_ids

# def format_response(results, intent, query):
#     if not results:
#         if intent == 'irrelevant':
#             return f"No information about '{query.lower().strip()}' is available."
#         return "No relevant information found for any profile."
#     if intent == 'names':
#         names = [r for r in results if not r.startswith("No ")]
#         if not names:
#             return "No profiles found."
#         return ", ".join(names)
#     if intent == 'count':
#         count = len([r for r in results if not r.startswith("No ")])
#         names = [r for r in results if not r.startswith("No ")]
#         return f"You have {count} profiles: {', '.join(names)}."
#     if intent == 'greeting':
#         return "Hello! How can I assist you with the profiles?"
#     if intent == 'irrelevant':
#         return f"No information about '{query.lower().strip()}' is available."
#     prompt = (
#         f"Format these results into a natural, fluent response without repetitive connectors like 'while':\n"
#         f"{json.dumps(results)}\n"
#         f"Use a single sentence or paragraph that flows naturally, e.g., "
#         f"'Arun has skills in CSS and React, Arvind has skills in Putty, and no skills are available for Bipin.' "
#         f"Strictly match the intent '{intent}' (e.g., only degrees for 'qualifications', only addresses for 'addresses'). "
#         f"Use 'degree' for qualifications consistently (e.g., 'B Tech degree', 'BCA degree'). "
#         f"No abbreviations unless in the data (e.g., 'BCA degree', not 'Bachelor of Computer Applications')."
#     )
#     return query_llm(prompt, max_tokens=300)

# def main(query):
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         # Extract intent and profiles
#         intent_data = extract_intent(query)
#         intent = intent_data.get('intent', 'all_data')
#         profiles = intent_data.get('profiles', [])
#         print(f"Processed intent data: {intent_data}", file=sys.stderr)

#         # Handle greeting or irrelevant queries
#         if intent in ['greeting', 'irrelevant']:
#             print(format_response([], intent, query))
#             return

#         # Handle count query
#         if intent == 'count':
#             profile_ids = get_profile_ids('all', cursor)
#             results = []
#             for name, profile_id in profile_ids:
#                 if profile_id:
#                     results.append(name.capitalize())
#                 else:
#                     results.append(f"No relevant information found for {name.capitalize()}.")
#             print(format_response(results, intent, query))
#             return

#         # Get profile IDs
#         profile_ids = get_profile_ids(profiles, cursor)
#         if not profile_ids:
#             print("No relevant profiles found.", file=sys.stderr)
#             print("No relevant profiles found.")
#             return

#         results = []
#         if intent == 'names':
#             for name, profile_id in profile_ids:
#                 if profile_id:
#                     results.append(name.capitalize())
#                 else:
#                     results.append(f"No relevant information found for {name.capitalize()}.")
#             print(format_response(results, intent, query))
#             return

#         query_embedding = get_embedding(query)
#         for name, profile_id in profile_ids:
#             if not profile_id:
#                 results.append(f"No relevant information found for {name.capitalize()}.")
#                 continue

#             # Fetch chunks
#             cursor.execute(
#                 "SELECT profile_id, chunk, embedding FROM embeddings WHERE profile_id = %s",
#                 [profile_id]
#             )
#             rows = cursor.fetchall()
#             print(f"Retrieved {len(rows)} embeddings for profile_id: {profile_id}", file=sys.stderr)

#             similarities = []
#             for row in rows:
#                 row_profile_id, chunk, embedding = row
#                 if not isinstance(embedding, list):
#                     embedding = json.loads(embedding)
#                 similarity = cosine_similarity(query_embedding, embedding)
#                 similarities.append((row_profile_id, chunk, similarity))
#                 print(f"Profile {row_profile_id}: Similarity {similarity:.4f}", file=sys.stderr)

#             similarities.sort(key=lambda x: x[2], reverse=True)
#             top_chunks = [s for s in similarities if s[2] > 0.6]
#             print(f"Top {len(top_chunks)} chunks selected for {name}", file=sys.stderr)

#             if not top_chunks:
#                 results.append(f"No relevant information found for {name.capitalize()}.")
#                 continue

#             prompt = (
#                 f"Answer the query '{query}' for the profile named '{name}'. "
#                 f"Use only these chunks and combine all relevant information into a concise natural language sentence. "
#                 f"Strictly focus on the requested intent ({intent}): "
#                 f"- 'skills': List only skills. "
#                 f"- 'qualifications': List only degrees (e.g., 'B Tech degree'). "
#                 f"- 'addresses': List only addresses. "
#                 f"- 'all_data': Include all available data (skills, qualifications, addresses). "
#                 f"Do not include profile IDs, similarity scores, or extraneous data. "
#                 f"Use 'degree' for qualifications (e.g., 'BCA degree')."
#             )
#             for i, (_, chunk, similarity) in enumerate(top_chunks):
#                 prompt += f"Chunk {i+1} (similarity: {similarity:.4f}): {chunk}\n"
#             print(f"Prompt for {name}: {prompt}", file=sys.stderr)

#             response = query_llm(prompt)
#             results.append(response)

#         # Format final response
#         print(format_response(results, intent, query))
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) < 2:
#         print("Error: Query argument required", file=sys.stderr)
#         sys.exit(1)
#     query = sys.argv[1]
#     main(query)




# import sys
# import os
# import psycopg2
# import numpy as np
# from openai import OpenAI
# from dotenv import load_dotenv
# import json
# import re

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

# def cosine_similarity(a, b):
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# def query_llm(prompt, max_tokens=200):
#     try:
#         response = client.chat.completions.create(
#             model='gpt-4o-mini',
#             messages=[
#                 {'role': 'system', 'content': 'You are a precise assistant that returns concise, natural language answers or structured JSON as requested. For profile queries, use only provided data, combining relevant information (e.g., skills) into a single list without duplicates. For multiple profiles, format responses fluently, avoiding repetitive connectors like "while." Use "degree" for qualifications consistently. For JSON, return clean JSON without markdown.'},
#                 {'role': 'user', 'content': prompt}
#             ],
#             max_tokens=max_tokens
#         )
#         content = response.choices[0].message.content.strip()
#         print(f"LLM response: {content}", file=sys.stderr)
#         return content
#     except Exception as e:
#         print(f"LLM error: {e}", file=sys.stderr)
#         raise

# def clean_json_response(response):
#     cleaned = re.sub(r'```json\s*|\s*```', '', response).strip()
#     try:
#         return json.loads(cleaned)
#     except json.JSONDecodeError as e:
#         print(f"JSON parse error: {e}, response: {cleaned}", file=sys.stderr)
#         return None

# def extract_intent(query):
#     intent_prompt = (
#         f"Analyze the query: '{query}'. Determine the intent and identify profile names or 'all profiles'. "
#         f"Return clean JSON with: "
#         f"- 'intent': 'skills', 'qualifications', 'addresses', 'names', 'count', 'greeting', 'irrelevant', or 'all_data' "
#         f"- 'profiles': ['name1', 'name2', ...] or 'all' "
#         f"Rules: "
#         f"- 'skills': Queries asking for skills (e.g., 'What all skills does Arun have?'). "
#         f"- 'qualifications': Queries asking for degrees or qualifications (e.g., 'What are all qualifications?'). "
#         f"- 'addresses': Queries asking for addresses (e.g., 'Provide address of Arun'). "
#         f"- 'names': Queries asking for profile names (e.g., 'Provide me all names'). "
#         f"- 'count': Queries asking for number of profiles (e.g., 'Total how many profiles do I have?'). "
#         f"- 'greeting': Short queries like 'Hi', 'Hello', 'Hey' (case-insensitive, with or without punctuation, including single words). "
#         f"- 'irrelevant': Queries unrelated to profiles (e.g., 'Most played game?'). "
#         f"- 'all_data': Generic profile queries (e.g., 'Tell me about all profiles'). "
#         f"- Consider 'all', 'all profiles', or similar as 'all'. "
#         f"- Handle typos (e.g., 'adres' as 'address'). "
#         f"- Prioritize 'greeting' for single-word queries like 'Hi' or 'hi'. "
#         f"Examples: "
#         f"- 'What all skills does Arvind have?' → {{'intent': 'skills', 'profiles': ['Arvind']}} "
#         f"- 'What are all Qualifications?' → {{'intent': 'qualifications', 'profiles': 'all'}} "
#         f"- 'Arun's adres is?' → {{'intent': 'addresses', 'profiles': ['Arun']}} "
#         f"- 'Hi' → {{'intent': 'greeting', 'profiles': []}} "
#         f"- 'Which game do Arun like?' → {{'intent': 'irrelevant', 'profiles': ['Arun']}} "
#     )
#     intent_response = query_llm(intent_prompt, max_tokens=100)
#     intent_data = clean_json_response(intent_response)
#     if intent_data:
#         print(f"Intent data from LLM: {intent_data}", file=sys.stderr)
#         return intent_data

#     # Fallback: regex
#     print("Falling back to regex parsing", file=sys.stderr)
#     query_lower = query.lower().strip()
#     intent = 'all_data'
#     profiles = []
#     if 'skill' in query_lower:
#         intent = 'skills'
#     elif 'qualification' in query_lower or 'degree' in query_lower:
#         intent = 'qualifications'
#     elif 'address' in query_lower or 'adres' in query_lower:
#         intent = 'addresses'
#     elif 'name' in query_lower:
#         intent = 'names'
#     elif 'how many' in query_lower or 'number of' in query_lower:
#         intent = 'count'
#     elif re.match(r'^(hi|hello|hey)(\?)?$', query_lower):
#         intent = 'greeting'
#     elif not query_lower.endswith('profiles?'):
#         intent = 'irrelevant'

#     if 'all profiles' in query_lower or 'all' in query_lower:
#         profiles = 'all'
#     else:
#         match = re.search(r'\b(of|for|does)\s+(.+?)(?:\s*\?|$)', query_lower)
#         if match:
#             names_str = match.group(2)
#             profiles = re.split(r'\s*(?:and|or|,)\s*', names_str)
#             profiles = [name.strip() for name in profiles if name.strip()]
#     intent_data = {'intent': intent, 'profiles': profiles}
#     print(f"Fallback intent data: {intent_data}", file=sys.stderr)
#     return intent_data

# def get_profile_ids(profiles, cursor):
#     profile_ids = []
#     if profiles == 'all':
#         cursor.execute("SELECT id, name FROM profiles ORDER BY name")
#         rows = cursor.fetchall()
#         for row in rows:
#             profile_ids.append((row[1], row[0]))
#             print(f"Found profile_id: {row[0]} for name: {row[1]}", file=sys.stderr)
#     else:
#         for name in profiles:
#             cursor.execute("SELECT id, name FROM profiles WHERE lower(name) = %s", [name.lower()])
#             result = cursor.fetchone()
#             if result:
#                 profile_ids.append((result[1], result[0]))
#                 print(f"Found profile_id: {result[0]} for name: {name}", file=sys.stderr)
#             else:
#                 profile_ids.append((name, None))
#                 print(f"No profile found for name: {name}", file=sys.stderr)
#     return profile_ids

# def format_response(results, intent, query):
#     if not results:
#         if intent == 'irrelevant':
#             return f"No information about '{query.lower().strip()}' is available."
#         return "No relevant information found for any profile."
#     if intent == 'names':
#         names = [r for r in results if not r.startswith("No ")]
#         if not names:
#             return "No profiles found."
#         return ", ".join(names)
#     if intent == 'count':
#         count = len([r for r in results if not r.startswith("No ")])
#         names = [r for r in results if not r.startswith("No ")]
#         return f"You have {count} profiles: {', '.join(names)}."
#     if intent == 'greeting':
#         return "Hello! How can I assist you with the profiles?"
#     if intent == 'irrelevant':
#         return f"No information about '{query.lower().strip()}' is available."
#     prompt = (
#         f"Format these results into a natural, fluent response without repetitive connectors like 'while':\n"
#         f"{json.dumps(results)}\n"
#         f"Use a single sentence or paragraph that flows naturally, e.g., "
#         f"'Arun has skills in CSS and React, Arvind has skills in Putty, and no skills are available for Bipin.' "
#         f"Strictly match the intent '{intent}': "
#         f"- 'skills': Include only skills. "
#         f"- 'qualifications': Include only degrees (e.g., 'B Tech degree'), no skills or other data. "
#         f"- 'addresses': Include only addresses. "
#         f"- 'all_data': Include all available data. "
#         f"Use 'degree' for qualifications consistently (e.g., 'BCA degree'). "
#         f"No abbreviations unless in the data (e.g., 'BCA degree', not 'Bachelor of Computer Applications')."
#     )
#     return query_llm(prompt, max_tokens=300)

# def main(query):
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         # Extract intent and profiles
#         intent_data = extract_intent(query)
#         intent = intent_data.get('intent', 'all_data')
#         profiles = intent_data.get('profiles', [])
#         print(f"Processed intent data: {intent_data}", file=sys.stderr)

#         # Handle greeting or irrelevant queries
#         if intent in ['greeting', 'irrelevant']:
#             print(format_response([], intent, query))
#             return

#         # Handle count query
#         if intent == 'count':
#             profile_ids = get_profile_ids('all', cursor)
#             results = []
#             for name, profile_id in profile_ids:
#                 if profile_id:
#                     results.append(name.capitalize())
#                 else:
#                     results.append(f"No relevant information found for {name.capitalize()}.")
#             print(format_response(results, intent, query))
#             return

#         # Get profile IDs
#         profile_ids = get_profile_ids(profiles, cursor)
#         if not profile_ids:
#             print("No relevant profiles found.", file=sys.stderr)
#             print("No relevant profiles found.")
#             return

#         results = []
#         if intent == 'names':
#             for name, profile_id in profile_ids:
#                 if profile_id:
#                     results.append(name.capitalize())
#                 else:
#                     results.append(f"No relevant information found for {name.capitalize()}.")
#             print(format_response(results, intent, query))
#             return

#         query_embedding = get_embedding(query)
#         for name, profile_id in profile_ids:
#             if not profile_id:
#                 results.append(f"No relevant information found for {name.capitalize()}.")
#                 continue

#             # Fetch chunks
#             cursor.execute(
#                 "SELECT profile_id, chunk, embedding FROM embeddings WHERE profile_id = %s",
#                 [profile_id]
#             )
#             rows = cursor.fetchall()
#             print(f"Retrieved {len(rows)} embeddings for profile_id: {profile_id}", file=sys.stderr)

#             similarities = []
#             for row in rows:
#                 row_profile_id, chunk, embedding = row
#                 if not isinstance(embedding, list):
#                     embedding = json.loads(embedding)
#                 similarity = cosine_similarity(query_embedding, embedding)
#                 similarities.append((row_profile_id, chunk, similarity))
#                 print(f"Profile {row_profile_id}: Similarity {similarity:.4f}", file=sys.stderr)

#             similarities.sort(key=lambda x: x[2], reverse=True)
#             top_chunks = [s for s in similarities if s[2] > 0.6]
#             print(f"Top {len(top_chunks)} chunks selected for {name}", file=sys.stderr)

#             if not top_chunks:
#                 results.append(f"No relevant information found for {name.capitalize()}.")
#                 continue

#             prompt = (
#                 f"Answer the query '{query}' for the profile named '{name}'. "
#                 f"Use only these chunks and combine all relevant information into a concise natural language sentence. "
#                 f"Strictly focus on the requested intent ({intent}): "
#                 f"- 'skills': List only skills. "
#                 f"- 'qualifications': List only degrees (e.g., 'B Tech degree'), exclude skills and other data. "
#                 f"- 'addresses': List only addresses. "
#                 f"- 'all_data': Include all available data (skills, qualifications, addresses). "
#                 f"Do not include profile IDs, similarity scores, or extraneous data. "
#                 f"Use 'degree' for qualifications (e.g., 'BCA degree')."
#             )
#             for i, (_, chunk, similarity) in enumerate(top_chunks):
#                 prompt += f"Chunk {i+1} (similarity: {similarity:.4f}): {chunk}\n"
#             print(f"Prompt for {name}: {prompt}", file=sys.stderr)

#             response = query_llm(prompt)
#             results.append(response)

#         # Format final response
#         print(format_response(results, intent, query))
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) < 2:
#         print("Error: Query argument required", file=sys.stderr)
#         sys.exit(1)
#     query = sys.argv[1]
#     main(query)


# import sys
# import os
# import psycopg2
# import numpy as np
# from openai import OpenAI
# from dotenv import load_dotenv
# import json
# import re

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

# def cosine_similarity(a, b):
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# def query_llm(prompt, max_tokens=200):
#     try:
#         response = client.chat.completions.create(
#             model='gpt-4o-mini',
#             messages=[
#                 {'role': 'system', 'content': 'You are a precise assistant that returns concise, natural language answers or structured JSON as requested. For profile queries, use only provided data, combining relevant information (e.g., skills) into a single list without duplicates. For multiple profiles, format responses fluently, avoiding repetitive connectors like "while." Use "degree" for qualifications consistently. For JSON, return clean JSON without markdown.'},
#                 {'role': 'user', 'content': prompt}
#             ],
#             max_tokens=max_tokens
#         )
#         content = response.choices[0].message.content.strip()
#         print(f"LLM response: {content}", file=sys.stderr)
#         return content
#     except Exception as e:
#         print(f"LLM error: {e}", file=sys.stderr)
#         raise

# def clean_json_response(response):
#     cleaned = re.sub(r'```json\s*|\s*```', '', response).strip()
#     try:
#         return json.loads(cleaned)
#     except json.JSONDecodeError as e:
#         print(f"JSON parse error: {e}, response: {cleaned}", file=sys.stderr)
#         return None

# def extract_intent(query):
#     # Normalize query
#     raw_query = query
#     query = query.strip()
#     print(f"Raw query: '{raw_query}'", file=sys.stderr)
#     print(f"Normalized query: '{query}'", file=sys.stderr)

#     intent_prompt = (
#         f"Analyze the query: '{query}'. Determine the intent and identify profile names or 'all profiles'. "
#         f"Return clean JSON with: "
#         f"- 'intent': 'skills', 'qualifications', 'addresses', 'names', 'count', 'greeting', 'irrelevant', or 'all_data' "
#         f"- 'profiles': ['name1', 'name2', ...] or 'all' "
#         f"Rules: "
#         f"- 'skills': Queries asking for skills (e.g., 'What all skills does Arun have?'). "
#         f"- 'qualifications': Queries asking for degrees or qualifications (e.g., 'What are all qualifications?'). "
#         f"- 'addresses': Queries asking for addresses (e.g., 'Provide address of Arun'). "
#         f"- 'names': Queries asking for profile names (e.g., 'Provide me all names'). "
#         f"- 'count': Queries asking for number of profiles (e.g., 'Total how many profiles do I have?'). "
#         f"- 'greeting': Queries exactly matching 'Hi', 'hi', 'Hello', 'hello', 'Hey', 'hey' (case-insensitive, with or without '?', no extra words). "
#         f"- 'irrelevant': Queries unrelated to profiles (e.g., 'Most played game?'). "
#         f"- 'all_data': Generic profile queries (e.g., 'Tell me about all profiles'). "
#         f"- Consider 'all', 'all profiles', or similar as 'all'. "
#         f"- Handle typos (e.g., 'adres' as 'address'). "
#         f"- If the query is a single word matching 'Hi', 'Hello', or 'Hey' (case-insensitive), return 'greeting'. "
#         f"Examples: "
#         f"- 'Hi' → {{'intent': 'greeting', 'profiles': []}} "
#         f"- 'hi?' → {{'intent': 'greeting', 'profiles': []}} "
#         f"- 'What all skills does Arvind have?' → {{'intent': 'skills', 'profiles': ['Arvind']}} "
#         f"- 'What are all Qualifications?' → {{'intent': 'qualifications', 'profiles': 'all'}} "
#         f"- 'Arun's adres is?' → {{'intent': 'addresses', 'profiles': ['Arun']}} "
#         f"- 'Which game do Arun like?' → {{'intent': 'irrelevant', 'profiles': ['Arun']}} "
#     )
#     intent_response = query_llm(intent_prompt, max_tokens=100)
#     intent_data = clean_json_response(intent_response)
#     if intent_data:
#         print(f"Intent data from LLM: {intent_data}", file=sys.stderr)
#         return intent_data

#     # Fallback: regex
#     print("Falling back to regex parsing", file=sys.stderr)
#     query_lower = query.lower().strip()
#     intent = 'all_data'
#     profiles = []
#     if 'skill' in query_lower:
#         intent = 'skills'
#     elif 'qualification' in query_lower or 'degree' in query_lower:
#         intent = 'qualifications'
#     elif 'address' in query_lower or 'adres' in query_lower:
#         intent = 'addresses'
#     elif 'name' in query_lower:
#         intent = 'names'
#     elif 'how many' in query_lower or 'number of' in query_lower:
#         intent = 'count'
#     elif re.match(r'^(hi|hello|hey)(\?)?\s*$', query_lower):
#         intent = 'greeting'
#     elif not query_lower.endswith('profiles?'):
#         intent = 'irrelevant'

#     if 'all profiles' in query_lower or 'all' in query_lower:
#         profiles = 'all'
#     else:
#         match = re.search(r'\b(of|for|does)\s+(.+?)(?:\s*\?|$)', query_lower)
#         if match:
#             names_str = match.group(2)
#             profiles = re.split(r'\s*(?:and|or|,)\s*', names_str)
#             profiles = [name.strip() for name in profiles if name.strip()]
#     intent_data = {'intent': intent, 'profiles': profiles}
#     print(f"Fallback intent data: {intent_data}", file=sys.stderr)
#     return intent_data

# def get_profile_ids(profiles, cursor):
#     profile_ids = []
#     if profiles == 'all':
#         cursor.execute("SELECT id, name FROM profiles ORDER BY name")
#         rows = cursor.fetchall()
#         for row in rows:
#             profile_ids.append((row[1], row[0]))
#             print(f"Found profile_id: {row[0]} for name: {row[1]}", file=sys.stderr)
#     else:
#         for name in profiles:
#             cursor.execute("SELECT id, name FROM profiles WHERE lower(name) = %s", [name.lower()])
#             result = cursor.fetchone()
#             if result:
#                 profile_ids.append((result[1], result[0]))
#                 print(f"Found profile_id: {result[0]} for name: {name}", file=sys.stderr)
#             else:
#                 profile_ids.append((name, None))
#                 print(f"No profile found for name: {name}", file=sys.stderr)
#     return profile_ids

# def format_response(results, intent, query):
#     if not results:
#         if intent == 'irrelevant':
#             return f"No information about '{query.lower().strip()}' is available."
#         return "No relevant information found for any profile."
#     if intent == 'names':
#         names = [r for r in results if not r.startswith("No ")]
#         if not names:
#             return "No profiles found."
#         return ", ".join(names)
#     if intent == 'count':
#         count = len([r for r in results if not r.startswith("No ")])
#         names = [r for r in results if not r.startswith("No ")]
#         return f"You have {count} profiles: {', '.join(names)}."
#     if intent == 'greeting':
#         return "Hello! How can I assist you with the profiles?"
#     if intent == 'irrelevant':
#         return f"No information about '{query.lower().strip()}' is available."
#     prompt = (
#         f"Format these results into a natural, fluent response without repetitive connectors like 'while':\n"
#         f"{json.dumps(results)}\n"
#         f"Use a single sentence or paragraph that flows naturally, e.g., "
#         f"'Arun has skills in CSS and React, Arvind has skills in Putty, and no skills are available for Bipin.' "
#         f"Strictly match the intent '{intent}': "
#         f"- 'skills': Include only skills. "
#         f"- 'qualifications': Include only degrees (e.g., 'B Tech degree'), no skills or other data. "
#         f"- 'addresses': Include only addresses. "
#         f"- 'all_data': Include all available data. "
#         f"Use 'degree' for qualifications consistently (e.g., 'BCA degree'). "
#         f"No abbreviations unless in the data (e.g., 'BCA degree', not 'Bachelor of Computer Applications')."
#     )
#     return query_llm(prompt, max_tokens=300)

# def main(query):
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         # Extract intent and profiles
#         intent_data = extract_intent(query)
#         intent = intent_data.get('intent', 'all_data')
#         profiles = intent_data.get('profiles', [])
#         print(f"Processed intent data: {intent_data}", file=sys.stderr)

#         # Handle greeting or irrelevant queries
#         if intent in ['greeting', 'irrelevant']:
#             print(format_response([], intent, query))
#             return

#         # Handle count query
#         if intent == 'count':
#             profile_ids = get_profile_ids('all', cursor)
#             results = []
#             for name, profile_id in profile_ids:
#                 if profile_id:
#                     results.append(name.capitalize())
#                 else:
#                     results.append(f"No relevant information found for {name.capitalize()}.")
#             print(format_response(results, intent, query))
#             return

#         # Get profile IDs
#         profile_ids = get_profile_ids(profiles, cursor)
#         if not profile_ids:
#             print("No relevant profiles found.", file=sys.stderr)
#             print("No relevant profiles found.")
#             return

#         results = []
#         if intent == 'names':
#             for name, profile_id in profile_ids:
#                 if profile_id:
#                     results.append(name.capitalize())
#                 else:
#                     results.append(f"No relevant information found for {name.capitalize()}.")
#             print(format_response(results, intent, query))
#             return

#         query_embedding = get_embedding(query)
#         for name, profile_id in profile_ids:
#             if not profile_id:
#                 results.append(f"No relevant information found for {name.capitalize()}.")
#                 continue

#             # Fetch chunks
#             cursor.execute(
#                 "SELECT profile_id, chunk, embedding FROM embeddings WHERE profile_id = %s",
#                 [profile_id]
#             )
#             rows = cursor.fetchall()
#             print(f"Retrieved {len(rows)} embeddings for profile_id: {profile_id}", file=sys.stderr)

#             similarities = []
#             for row in rows:
#                 row_profile_id, chunk, embedding = row
#                 if not isinstance(embedding, list):
#                     embedding = json.loads(embedding)
#                 similarity = cosine_similarity(query_embedding, embedding)
#                 similarities.append((row_profile_id, chunk, similarity))
#                 print(f"Profile {row_profile_id}: Similarity {similarity:.4f}", file=sys.stderr)

#             similarities.sort(key=lambda x: x[2], reverse=True)
#             top_chunks = [s for s in similarities if s[2] > 0.6]
#             print(f"Top {len(top_chunks)} chunks selected for {name}", file=sys.stderr)

#             if not top_chunks:
#                 results.append(f"No relevant information found for {name.capitalize()}.")
#                 continue

#             prompt = (
#                 f"Answer the query '{query}' for the profile named '{name}'. "
#                 f"Use only these chunks and combine all relevant information into a concise natural language sentence. "
#                 f"Strictly focus on the requested intent ({intent}): "
#                 f"- 'skills': List only skills. "
#                 f"- 'qualifications': List only degrees (e.g., 'B Tech degree'), exclude skills and other data. "
#                 f"- 'addresses': List only addresses. "
#                 f"- 'all_data': Include all available data (skills, qualifications, addresses). "
#                 f"Do not include profile IDs, similarity scores, or extraneous data. "
#                 f"Use 'degree' for qualifications (e.g., 'BCA degree')."
#             )
#             for i, (_, chunk, similarity) in enumerate(top_chunks):
#                 prompt += f"Chunk {i+1} (similarity: {similarity:.4f}): {chunk}\n"
#             print(f"Prompt for {name}: {prompt}", file=sys.stderr)

#             response = query_llm(prompt)
#             results.append(response)

#         # Format final response
#         print(format_response(results, intent, query))
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) < 2:
#         print("Error: Query argument required", file=sys.stderr)
#         sys.exit(1)
#     query = sys.argv[1]
#     main(query)




# working very fine but use of much prompts
# import sys
# import os
# import psycopg2
# import numpy as np
# from openai import OpenAI
# from dotenv import load_dotenv
# import json
# import re

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

# def cosine_similarity(a, b):
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# def query_llm(prompt, max_tokens=200):
#     try:
#         response = client.chat.completions.create(
#             model='gpt-4o-mini',
#             messages=[
#                 {'role': 'system', 'content': 'You are a precise assistant that returns concise, natural language answers or structured JSON as requested. For profile queries, use only provided data, combining relevant information (e.g., skills) into a single list without duplicates. For multiple profiles, format responses fluently, avoiding repetitive connectors like "while." Use "degree" for qualifications consistently. For JSON, return clean JSON without markdown. For greetings, respond with a friendly, natural greeting like "Hello! How can I assist you with the profiles?"'},
#                 {'role': 'user', 'content': prompt}
#             ],
#             max_tokens=max_tokens
#         )
#         content = response.choices[0].message.content.strip()
#         print(f"LLM response: {content}", file=sys.stderr)
#         return content
#     except Exception as e:
#         print(f"LLM error: {e}", file=sys.stderr)
#         raise

# def clean_json_response(response):
#     cleaned = re.sub(r'```json\s*|\s*```', '', response).strip()
#     try:
#         return json.loads(cleaned)
#     except json.JSONDecodeError as e:
#         print(f"JSON parse error: {e}, response: {cleaned}", file=sys.stderr)
#         return None

# def extract_intent(query):
#     raw_query = query
#     query = query.strip()
#     print(f"Raw query: '{raw_query}'", file=sys.stderr)
#     print(f"Normalized query: '{query}'", file=sys.stderr)

#     intent_prompt = (
#         f"Analyze the query: '{query}'. Determine the intent and identify profile names or 'all profiles'. "
#         f"Return clean JSON with: "
#         f"- 'intent': 'skills', 'qualifications', 'addresses', 'names', 'count', 'greeting', 'irrelevant', or 'all_data' "
#         f"- 'profiles': ['name1', 'name2', ...] or 'all' "
#         f"Rules: "
#         f"- 'skills': Queries asking for skills (e.g., 'What all skills does Arun have?'). "
#         f"- 'qualifications': Queries asking for degrees or qualifications (e.g., 'What are all qualifications?'). "
#         f"- 'addresses': Queries asking for addresses (e.g., 'Provide address of Arun'). "
#         f"- 'names': Queries asking for profile names (e.g., 'Provide me all names'). "
#         f"- 'count': Queries asking for number of profiles (e.g., 'Total how many profiles do I have?'). "
#         f"- 'greeting': Queries exactly matching 'Hi', 'hi', 'Hello', 'hello', 'Hey', 'hey' (case-insensitive, with or without '?', no extra words). "
#         f"- 'irrelevant': Queries unrelated to profiles (e.g., 'Most played game?'). "
#         f"- 'all_data': Generic profile queries (e.g., 'Tell me about all profiles'). "
#         f"- Consider 'all', 'all profiles', or similar as 'all'. "
#         f"- Handle typos (e.g., 'adres' as 'address'). "
#         f"- If the query is a single word matching 'Hi', 'Hello', or 'Hey' (case-insensitive), return 'greeting'. "
#         f"Examples: "
#         f"- 'Hi' → {{'intent': 'greeting', 'profiles': []}} "
#         f"- 'hi?' → {{'intent': 'greeting', 'profiles': []}} "
#         f"- 'What all skills does Arvind have?' → {{'intent': 'skills', 'profiles': ['Arvind']}} "
#         f"- 'What are all Qualifications?' → {{'intent': 'qualifications', 'profiles': 'all'}} "
#         f"- 'Arun's adres is?' → {{'intent': 'addresses', 'profiles': ['Arun']}} "
#         f"- 'Which game do Arun like?' → {{'intent': 'irrelevant', 'profiles': ['Arun']}} "
#     )
#     intent_response = query_llm(intent_prompt, max_tokens=100)
#     intent_data = clean_json_response(intent_response)
#     if intent_data:
#         print(f"Intent data from LLM: {intent_data}", file=sys.stderr)
#         return intent_data

#     # Fallback: regex
#     print("Falling back to regex parsing", file=sys.stderr)
#     query_lower = query.lower().strip()
#     intent = 'all_data'
#     profiles = []
#     if 'skill' in query_lower:
#         intent = 'skills'
#     elif 'qualification' in query_lower or 'degree' in query_lower:
#         intent = 'qualifications'
#     elif 'address' in query_lower or 'adres' in query_lower:
#         intent = 'addresses'
#     elif 'name' in query_lower:
#         intent = 'names'
#     elif 'how many' in query_lower or 'number of' in query_lower:
#         intent = 'count'
#     elif re.match(r'^(hi|hello|hey)(\?)?\s*$', query_lower):
#         intent = 'greeting'
#     elif not query_lower.endswith('profiles?'):
#         intent = 'irrelevant'

#     if 'all profiles' in query_lower or 'all' in query_lower:
#         profiles = 'all'
#     else:
#         match = re.search(r'\b(of|for|does)\s+(.+?)(?:\s*\?|$)', query_lower)
#         if match:
#             names_str = match.group(2)
#             profiles = re.split(r'\s*(?:and|or|,)\s*', names_str)
#             profiles = [name.strip() for name in profiles if name.strip()]
#     intent_data = {'intent': intent, 'profiles': profiles}
#     print(f"Fallback intent data: {intent_data}", file=sys.stderr)
#     return intent_data

# def get_profile_ids(profiles, cursor):
#     profile_ids = []
#     if profiles == 'all':
#         cursor.execute("SELECT id, name FROM profiles ORDER BY name")
#         rows = cursor.fetchall()
#         for row in rows:
#             profile_ids.append((row[1], row[0]))
#             print(f"Found profile_id: {row[0]} for name: {row[1]}", file=sys.stderr)
#     else:
#         for name in profiles:
#             cursor.execute("SELECT id, name FROM profiles WHERE lower(name) = %s", [name.lower()])
#             result = cursor.fetchone()
#             if result:
#                 profile_ids.append((result[1], result[0]))
#                 print(f"Found profile_id: {result[0]} for name: {name}", file=sys.stderr)
#             else:
#                 profile_ids.append((name, None))
#                 print(f"No profile found for name: {name}", file=sys.stderr)
#     return profile_ids

# def format_response(results, intent, query):
#     print(f"Formatting response for intent: {intent}, results: {results}, query: {query}", file=sys.stderr)
#     if not results:
#         if intent == 'irrelevant':
#             return f"No information about '{query.lower().strip()}' is available."
#         return "No relevant information found for any profile."
#     if intent == 'names':
#         names = [r for r in results if not r.startswith("No ")]
#         if not names:
#             return "No profiles found."
#         return ", ".join(names)
#     if intent == 'count':
#         count = len([r for r in results if not r.startswith("No ")])
#         names = [r for r in results if not r.startswith("No ")]
#         return f"You have {count} profiles: {', '.join(names)}."
#     prompt = (
#         f"Format these results into a natural, fluent response without repetitive connectors like 'while':\n"
#         f"{json.dumps(results)}\n"
#         f"Use a single sentence or paragraph that flows naturally, e.g., "
#         f"'Arun has skills in CSS and React, Arvind has skills in Putty, and no skills are available for Bipin.' "
#         f"Strictly match the intent '{intent}': "
#         f"- 'skills': Include only skills. "
#         f"- 'qualifications': Include only degrees (e.g., 'B Tech degree'), no skills or other data. "
#         f"- 'addresses': Include only addresses. "
#         f"- 'all_data': Include all available data. "
#         f"Use 'degree' for qualifications consistently (e.g., 'BCA degree'). "
#         f"No abbreviations unless in the data (e.g., 'BCA degree', not 'Bachelor of Computer Applications')."
#     )
#     return query_llm(prompt, max_tokens=300)

# def main(query):
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         # Extract intent and profiles
#         intent_data = extract_intent(query)
#         intent = intent_data.get('intent', 'all_data')
#         profiles = intent_data.get('profiles', [])
#         print(f"Processed intent data: {intent_data}", file=sys.stderr)

#         # Handle greeting
#         if intent == 'greeting':
#             prompt = f"The user said '{query}'. Respond with a friendly, natural greeting."
#             response = query_llm(prompt, max_tokens=50)
#             print(f"Final response: {response}", file=sys.stderr)
#             print(response)
#             return

#         # Handle irrelevant queries
#         if intent == 'irrelevant':
#             response = f"No information about '{query.lower().strip()}' is available."
#             print(f"Final response: {response}", file=sys.stderr)
#             print(response)
#             return

#         # Handle count query
#         if intent == 'count':
#             profile_ids = get_profile_ids('all', cursor)
#             results = []
#             for name, profile_id in profile_ids:
#                 if profile_id:
#                     results.append(name.capitalize())
#                 else:
#                     results.append(f"No relevant information found for {name.capitalize()}.")
#             response = format_response(results, intent, query)
#             print(f"Final response: {response}", file=sys.stderr)
#             print(response)
#             return

#         # Get profile IDs
#         profile_ids = get_profile_ids(profiles, cursor)
#         if not profile_ids:
#             response = "No relevant profiles found."
#             print(f"Final response: {response}", file=sys.stderr)
#             print(response)
#             return

#         results = []
#         if intent == 'names':
#             for name, profile_id in profile_ids:
#                 if profile_id:
#                     results.append(name.capitalize())
#                 else:
#                     results.append(f"No relevant information found for {name.capitalize()}.")
#             response = format_response(results, intent, query)
#             print(f"Final response: {response}", file=sys.stderr)
#             print(response)
#             return

#         query_embedding = get_embedding(query)
#         for name, profile_id in profile_ids:
#             if not profile_id:
#                 results.append(f"No relevant information found for {name.capitalize()}.")
#                 continue

#             # Fetch chunks
#             cursor.execute(
#                 "SELECT profile_id, chunk, embedding FROM embeddings WHERE profile_id = %s",
#                 [profile_id]
#             )
#             rows = cursor.fetchall()
#             print(f"Retrieved {len(rows)} embeddings for profile_id: {profile_id}", file=sys.stderr)

#             similarities = []
#             for row in rows:
#                 row_profile_id, chunk, embedding = row
#                 if not isinstance(embedding, list):
#                     embedding = json.loads(embedding)
#                 similarity = cosine_similarity(query_embedding, embedding)
#                 similarities.append((row_profile_id, chunk, similarity))
#                 print(f"Profile {row_profile_id}: Similarity {similarity:.4f}", file=sys.stderr)

#             similarities.sort(key=lambda x: x[2], reverse=True)
#             top_chunks = [s for s in similarities if s[2] > 0.6]
#             print(f"Top {len(top_chunks)} chunks selected for {name}", file=sys.stderr)

#             if not top_chunks:
#                 results.append(f"No relevant information found for {name.capitalize()}.")
#                 continue

#             prompt = (
#                 f"Answer the query '{query}' for the profile named '{name}'. "
#                 f"Use only these chunks and combine all relevant information into a concise natural language sentence. "
#                 f"Strictly focus on the requested intent ({intent}): "
#                 f"- 'skills': List only skills. "
#                 f"- 'qualifications': List only degrees (e.g., 'B Tech degree'), exclude skills and other data. "
#                 f"- 'addresses': List only addresses. "
#                 f"- 'all_data': Include all available data (skills, qualifications, addresses). "
#                 f"Do not include profile IDs, similarity scores, or extraneous data. "
#                 f"Use 'degree' for qualifications (e.g., 'BCA degree')."
#             )
#             for i, (_, chunk, similarity) in enumerate(top_chunks):
#                 prompt += f"Chunk {i+1} (similarity: {similarity:.4f}): {chunk}\n"
#             print(f"Prompt for {name}: {prompt}", file=sys.stderr)

#             response = query_llm(prompt)
#             results.append(response)

#         # Format final response
#         response = format_response(results, intent, query)
#         print(f"Final response: {response}", file=sys.stderr)
#         print(response)
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) < 2:
#         print("Error: Query argument required", file=sys.stderr)
#         sys.exit(1)
#     query = sys.argv[1]
#     main(query)



import sys
import os
import psycopg2
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
import json
import re

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

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def query_llm(prompt, max_tokens=200):
    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {'role': 'system', 'content': 'You are a precise assistant that answers questions based only on provided profile data. Use natural, concise language. For greetings (e.g., "Hi"), respond with a friendly greeting like "Hello! How can I assist you with the profiles?". For irrelevant queries, say "No information available for this query." Use "degree" for qualifications (e.g., "BCA degree"). Combine multiple profile answers fluently, avoiding repetitive connectors like "while".'},
                {'role': 'user', 'content': prompt}
            ],
            max_tokens=max_tokens
        )
        content = response.choices[0].message.content.strip()
        print(f"LLM response: {content}", file=sys.stderr)
        return content
    except Exception as e:
        print(f"LLM error: {e}", file=sys.stderr)
        raise

def get_profile_ids(query, cursor):
    query_lower = query.lower().strip()
    # Check for specific names or 'all'
    if 'all' in query_lower or 'every' in query_lower:
        cursor.execute("SELECT id, name FROM profiles ORDER BY name")
        rows = cursor.fetchall()
        profile_ids = [(row[1], row[0]) for row in rows]
        print(f"Found profiles: {[name for name, _ in profile_ids]}", file=sys.stderr)
        return profile_ids
    # Extract names using simple regex
    match = re.search(r'\b(of|for|does)\s+(.+?)(?:\s*\?|$)', query_lower)
    if match:
        names_str = match.group(2)
        names = re.split(r'\s*(?:and|or|,)\s*', names_str)
        names = [name.strip() for name in names if name.strip()]
    else:
        names = []
    if not names:
        return []
    profile_ids = []
    for name in names:
        cursor.execute("SELECT id, name FROM profiles WHERE lower(name) = %s", [name.lower()])
        result = cursor.fetchone()
        if result:
            profile_ids.append((result[1], result[0]))
            print(f"Found profile_id: {result[0]} for name: {name}", file=sys.stderr)
        else:
            profile_ids.append((name, None))
            print(f"No profile found for name: {name}", file=sys.stderr)
    return profile_ids

def main(query):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Normalize query
        query = query.strip()
        print(f"Raw query: '{query}'", file=sys.stderr)

        # Handle greeting directly
        if re.match(r'^(hi|hello|hey)(\?)?\s*$', query.lower(), re.IGNORECASE):
            response = query_llm("The user said a greeting. Respond with a friendly greeting.", max_tokens=50)
            print(f"Final response: {response}", file=sys.stderr)
            print(response)
            return

        # Get profile IDs
        profile_ids = get_profile_ids(query, cursor)
        if not profile_ids:
            response = query_llm(f"The query '{query}' does not specify any valid profiles. Respond appropriately.", max_tokens=50)
            print(f"Final response: {response}", file=sys.stderr)
            print(response)
            return

        results = []
        query_embedding = get_embedding(query)
        for name, profile_id in profile_ids:
            if not profile_id:
                results.append(f"No information available for {name.capitalize()}.")
                continue

            # Fetch chunks
            cursor.execute(
                "SELECT profile_id, chunk, embedding FROM embeddings WHERE profile_id = %s",
                [profile_id]
            )
            rows = cursor.fetchall()
            print(f"Retrieved {len(rows)} embeddings for profile_id: {profile_id}", file=sys.stderr)

            similarities = []
            for row in rows:
                row_profile_id, chunk, embedding = row
                if not isinstance(embedding, list):
                    embedding = json.loads(embedding)
                similarity = cosine_similarity(query_embedding, embedding)
                similarities.append((row_profile_id, chunk, similarity))
                print(f"Profile {row_profile_id}: Similarity {similarity:.4f}", file=sys.stderr)

            similarities.sort(key=lambda x: x[2], reverse=True)
            top_chunks = [s for s in similarities if s[2] > 0.6]
            print(f"Top {len(top_chunks)} chunks selected for {name}", file=sys.stderr)

            if not top_chunks:
                results.append(f"No relevant information found for {name.capitalize()}.")
                continue

            # Minimal prompt with context
            prompt = (
                f"Answer the query '{query}' for the profile named '{name}' using only the following data:\n"
            )
            for i, (_, chunk, similarity) in enumerate(top_chunks):
                prompt += f"Data {i+1}: {chunk}\n"
            prompt += (
                f"Provide a concise, natural answer based only on the data. "
                f"If the query asks for qualifications, include only degrees (e.g., 'B Tech degree'), excluding skills. "
                f"If no relevant data is found, say 'No relevant information found for {name.capitalize()}.'"
            )
            response = query_llm(prompt, max_tokens=100)
            results.append(response)

        # Combine results
        if not results or all(r.startswith("No ") for r in results):
            response = "No relevant information found for any profile."
        else:
            prompt = (
                f"Combine these results into a single, fluent response:\n"
                f"{json.dumps(results)}\n"
                f"Use natural language, e.g., 'Arun has skills in CSS and React, and Arvind has skills in Putty.' "
                f"If the query asks for qualifications, include only degrees, excluding skills."
            )
            response = query_llm(prompt, max_tokens=300)
        print(f"Final response: {response}", file=sys.stderr)
        print(response)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Error: Query argument required", file=sys.stderr)
        sys.exit(1)
    query = sys.argv[1]
    main(query)