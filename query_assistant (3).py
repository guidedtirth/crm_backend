#  after assistant api
# import sys
# import psycopg2
# from openai import OpenAI
# from dotenv import load_dotenv
# import os
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

# def get_assistant_id(assistant_name):
#     try:
#         assistants = client.beta.assistants.list()
#         for assistant in assistants.data:
#             if assistant.name == assistant_name:
#                 print(f"Found assistant: {assistant_name}", file=sys.stderr)
#                 return assistant.id
#         print(f"No assistant found for name: {assistant_name}", file=sys.stderr)
#         return None
#     except Exception as e:
#         print(f"Assistant retrieval error: {e}", file=sys.stderr)
#         raise

# def query_assistant(assistant_id, profile_content, job_data):
#     try:
#         thread = client.beta.threads.create()
#         message = client.beta.threads.messages.create(
#             thread_id=thread.id,
#             role="user",
#             content=(
#                 f"Profile content:\n{profile_content}\n\n"
#                 f"Job:\n"
#                 f"Title: {job_data['title']}\n"
#                 f"Description: {job_data['description']}\n"
#                 f"Skills: {', '.join(job_data['skills'])}\n"
#                 f"Budget: ${job_data['budgetMin']}–${job_data['budgetMax']}\n"
#                 f"Evaluate relevance and return JSON with 'relevance', 'score', and 'reason'."
#             )
#         )
#         run = client.beta.threads.runs.create(
#             thread_id=thread.id,
#             assistant_id=assistant_id
#         )
#         while run.status != 'completed':
#             run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
#         messages = client.beta.threads.messages.list(thread_id=thread.id)
#         response = messages.data[0].content[0].text.value
#         print(f"Assistant response: {response}", file=sys.stderr)
#         return json.loads(response)
#     except Exception as e:
#         print(f"Assistant query error: {e}", file=sys.stderr)
#         raise

# def main(query_json):
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         # Parse job query
#         job_data = json.loads(query_json)
#         print(f"Job data: {job_data}", file=sys.stderr)

#         # Get Ruchi’s profile content and assistant_name
#         cursor.execute("SELECT content, assistant_name FROM profiles WHERE name = 'Ruchi Agrawal'")
#         result = cursor.fetchone()
#         if not result or not result[0]:
#             print("No profile content for Ruchi Agrawal", file=sys.stderr)
#             return {"relevance": "No", "score": 0, "reason": "Profile data not found"}

#         profile_content, assistant_name = result
#         if not assistant_name:
#             print("No assistant for Ruchi Agrawal", file=sys.stderr)
#             return {"relevance": "No", "score": 0, "reason": "Assistant not configured"}

#         # Get assistant ID
#         assistant_id = get_assistant_id(assistant_name)
#         if not assistant_id:
#             print(f"Assistant {assistant_name} not found in OpenAI", file=sys.stderr)
#             return {"relevance": "No", "score": 0, "reason": "Assistant not found"}

#         # Query assistant
#         response = query_assistant(assistant_id, profile_content, job_data)
#         print(f"Final response: {response}", file=sys.stderr)
#         print(json.dumps(response))
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         cursor.close()
#         conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) < 2:
#         print("Error: Query JSON required", file=sys.stderr)
#         sys.exit(1)
#     query_json = sys.argv[1]
#     main(query_json)


# import sys
# import psycopg2
# from openai import OpenAI
# from dotenv import load_dotenv
# import os
# import json
# import numpy as np

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

# def get_query_embedding(query_text):
#     try:
#         response = client.embeddings.create(
#             input=query_text,
#             model="text-embedding-ada-002"
#         )
#         return response.data[0].embedding
#     except Exception as e:
#         print(f"Query embedding error: {e}", file=sys.stderr)
#         raise

# def cosine_similarity(a, b):
#     a = np.array(a)
#     b = np.array(b)
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# def main(query_file):
#     try:
#         with open(query_file, 'r', encoding='utf-8') as f:
#             query = json.load(f)
#         query_text = f"{query['title']} {query['description']} {' '.join(query['skills'])}"
#         print(f"Read query from {query_file}: {query['title']}", file=sys.stderr)

#         query_embedding = get_query_embedding(query_text)
#         print(f"Generated query embedding", file=sys.stderr)

#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         cursor.execute("SELECT profile_id, chunk, embedding FROM embeddings")
#         embeddings = cursor.fetchall()
#         print(f"Retrieved {len(embeddings)} embeddings", file=sys.stderr)

#         best_match = None
#         highest_score = -1
#         best_profile_id = None

#         for profile_id, chunk, embedding_json in embeddings:
#             embedding = json.loads(embedding_json)
#             score = cosine_similarity(query_embedding, embedding)
#             if score > highest_score:
#                 highest_score = score
#                 best_match = chunk
#                 best_profile_id = profile_id

#         if highest_score < 0.5:
#             result = {
#                 "relevance": "No",
#                 "score": int(highest_score * 100),
#                 "reason": "No sufficiently relevant profile found"
#             }
#         else:
#             cursor.execute(
#                 "SELECT name, content FROM profiles WHERE id = %s",
#                 (best_profile_id,)
#             )
#             profile = cursor.fetchone()
#             profile_name = profile[0]
#             profile_content = profile[1]

#             response = client.chat.completions.create(
#                 model="gpt-4o-mini",
#                 messages=[
#                     {
#                         "role": "system",
#                         "content": "Evaluate job relevance based on profile content."
#                     },
#                     {
#                         "role": "user",
#                         "content": f"Profile: {profile_content}\nJob: {query_text}\nIs this job relevant? Provide a score (0-100) and reason."
#                     }
#                 ]
#             )
#             gpt_response = response.choices[0].message.content
#             score = int(highest_score * 100)
#             result = {
#                 "relevance": "Yes",
#                 "score": score,
#                 "reason": gpt_response
#             }
#             print(f"Matched profile: {profile_name} with score: {score}", file=sys.stderr)

#         print(json.dumps(result))
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) != 2:
#         print("Error: Expected query file path as argument", file=sys.stderr)
#         sys.exit(1)
#     query_file = sys.argv[1]
#     main(query_file)

# working by use of embeddings api and chat completions
# import sys
# import psycopg2
# from openai import OpenAI
# from dotenv import load_dotenv
# import os
# import json
# import numpy as np

# # Load environment variables
# load_dotenv()

# # Database configuration
# DB_CONFIG = {
#     'dbname': os.getenv('DB_NAME', 'profiledb'),
#     'user': os.getenv('DB_USER', 'profile'),
#     'password': os.getenv('DB_PASSWORD', 'profileUYh$13#'),
#     'host': os.getenv('DB_HOST', '122.176.158.168'),
#     'port': os.getenv('DB_PORT', '5432'),
#     'sslmode': 'require'
# }

# # Initialize OpenAI client
# client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# def get_query_embedding(query_text):
#     try:
#         print(f"Generating embedding for query: {query_text[:50]}...", file=sys.stderr)
#         response = client.embeddings.create(
#             input=query_text,
#             model="text-embedding-ada-002"
#         )
#         embedding = response.data[0].embedding
#         print(f"Query embedding generated, length: {len(embedding)}", file=sys.stderr)
#         return embedding
#     except Exception as e:
#         print(f"Query embedding error: {e}", file=sys.stderr)
#         raise

# def cosine_similarity(a, b):
#     a = np.array(a)
#     b = np.array(b)
#     score = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
#     print(f"Calculated cosine similarity: {score}", file=sys.stderr)
#     return score

# def main(query_file):
#     try:
#         # Read and parse query file
#         print(f"Reading query file: {query_file}", file=sys.stderr)
#         if not os.path.exists(query_file):
#             print(f"Error: Query file not found: {query_file}", file=sys.stderr)
#             sys.exit(1)
        
#         with open(query_file, 'r', encoding='utf-8') as f:
#             content = f.read()
#             print(f"Query file content: {content[:200]}...", file=sys.stderr)
#             query = json.loads(content)
#         query_text = f"{query['title']} {query['description']} {' '.join(query['skills'])}"
#         print(f"Parsed query title: {query['title']}", file=sys.stderr)

#         # Generate query embedding
#         query_embedding = get_query_embedding(query_text)

#         # Connect to database
#         print("Connecting to database...", file=sys.stderr)
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         # Retrieve embeddings
#         cursor.execute("SELECT profile_id, chunk, embedding FROM embeddings")
#         embeddings = cursor.fetchall()
#         print(f"Retrieved {len(embeddings)} embeddings", file=sys.stderr)

#         best_match = None
#         highest_score = -1
#         best_profile_id = None

#         # Process embeddings
#         for profile_id, chunk, embedding_json in embeddings:
#             print(f"Processing embedding for profile_id: {profile_id}, chunk: {chunk[:50]}...", file=sys.stderr)
#             try:
#                 # Ensure embedding_json is a string before parsing
#                 if isinstance(embedding_json, str):
#                     embedding = json.loads(embedding_json)
#                 elif isinstance(embedding_json, list):
#                     embedding = embedding_json  # Already a list, no parsing needed
#                 else:
#                     print(f"Error: Unexpected embedding type: {type(embedding_json)}", file=sys.stderr)
#                     continue

#                 # Verify embedding is a list of numbers
#                 if not isinstance(embedding, list) or not all(isinstance(x, (int, float)) for x in embedding):
#                     print(f"Error: Invalid embedding format for profile_id: {profile_id}", file=sys.stderr)
#                     continue

#                 score = cosine_similarity(query_embedding, embedding)
#                 print(f"Score for profile_id {profile_id}: {score}", file=sys.stderr)
#                 if score > highest_score:
#                     highest_score = score
#                     best_match = chunk
#                     best_profile_id = profile_id
#             except json.JSONDecodeError as e:
#                 print(f"JSON parsing error for embedding (profile_id: {profile_id}): {e}", file=sys.stderr)
#                 continue

#         if highest_score < 0.5:
#             result = {
#                 "relevance": "No",
#                 "score": int(highest_score * 100),
#                 "reason": "No sufficiently relevant profile found"
#             }
#             print(f"No relevant profile found, highest score: {highest_score}", file=sys.stderr)
#         else:
#             # Fetch profile details
#             cursor.execute(
#                 "SELECT name, content FROM profiles WHERE id = %s",
#                 (best_profile_id,)
#             )
#             profile = cursor.fetchone()
#             if not profile:
#                 print(f"Error: No profile found for profile_id: {best_profile_id}", file=sys.stderr)
#                 result = {
#                     "relevance": "No",
#                     "score": int(highest_score * 100),
#                     "reason": "Profile not found in database"
#                 }
#             else:
#                 profile_name, profile_content = profile
#                 print(f"Found profile: {profile_name}, content length: {len(profile_content)}", file=sys.stderr)

#                 # Evaluate job relevance with GPT
#                 print("Sending request to GPT-4o-mini...", file=sys.stderr)
#                 response = client.chat.completions.create(
#                     model="gpt-4o-mini",
#                     messages=[
#                         {
#                             "role": "system",
#                             "content": "Evaluate job relevance based on profile content."
#                         },
#                         {
#                             "role": "user",
#                             "content": f"Profile: {profile_content}\nJob: {query_text}\nIs this job relevant? Provide a score (0-100) and reason."
#                         }
#                     ]
#                 )
#                 gpt_response = response.choices[0].message.content
#                 print(f"GPT response: {gpt_response[:200]}...", file=sys.stderr)
#                 score = int(highest_score * 100)
#                 result = {
#                     "relevance": "Yes",
#                     "score": score,
#                     "reason": gpt_response
#                 }
#                 print(f"Matched profile: {profile_name} with score: {score}", file=sys.stderr)

#         # Output result
#         print(json.dumps(result))
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()
#         print("Database connection closed", file=sys.stderr)

# if __name__ == '__main__':
#     if len(sys.argv) != 2:
#         print("Error: Expected query file path as argument", file=sys.stderr)
#         sys.exit(1)
#     query_file = sys.argv[1]
#     main(query_file)






# in this hardcoded prompt so no use of embeddings
# import sys
# import json
# from openai import OpenAI
# from dotenv import load_dotenv
# import os

# # Load environment variables
# load_dotenv()

# # Initialize OpenAI client
# client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# def create_assistant():
#     try:
#         assistant = client.beta.assistants.create(
#             name="Freelance Job Filter",
#             instructions="You are a freelance job filter assistant. Given a user profile and a job post, evaluate if the job is relevant. Return the response in JSON format: {\"relevance\": \"Yes/No\", \"score\": number, \"reason\": \"short summary\"}. Consider the profile's skills, experience, preferences, and constraints (e.g., avoid vague or low-budget jobs).",
#             model="gpt-4o-mini",
#             tools=[],
#             response_format={"type": "json_object"}
#         )
#         print(f"Created assistant: {assistant.id}", file=sys.stderr)
#         return assistant
#     except Exception as e:
#         print(f"Assistant creation error: {e}", file=sys.stderr)
#         raise

# def evaluate_job(assistant, profile, job, thread):
#     try:
#         # Prepare prompt
#         prompt = (
#             f"--- My Profile ---\n"
#             f"- 20+ yrs in dev & project mgmt\n"
#             f"- Expert in n8n, Zapier, Make.com\n"
#             f"- Skilled: GPT-4, Twilio, Node.js, Supabase\n"
#             f"- Prefers automation/AI workflows\n"
#             f"- Avoids vague, low-budget jobs (<$300)\n\n"
#             f"--- Job ---\n"
#             f"Title: {job['title']}\n\n"
#             f"Description: {job['description']}\n\n"
#             f"Skills: {', '.join(job['skills'])}\n\n"
#             f"Budget: ${job['budgetMin']}–${job['budgetMax']}\n\n"
#             f"Return: JSON with relevance (Yes/No), score (0–100), and short reason."
#         )
        
#         # Add prompt to thread
#         client.beta.threads.messages.create(
#             thread_id=thread.id,
#             role="user",
#             content=prompt
#         )
        
#         # Run assistant
#         run = client.beta.threads.runs.create(
#             thread_id=thread.id,
#             assistant_id=assistant.id
#         )
        
#         # Poll for completion
#         while run.status != "completed":
#             run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
#             print(f"Run status: {run.status}", file=sys.stderr)
        
#         # Retrieve response
#         messages = client.beta.threads.messages.list(thread_id=thread.id)
#         response = json.loads(messages.data[0].content[0].text.value)
#         print(f"Assistant response: {json.dumps(response)[:200]}...", file=sys.stderr)
#         return response
#     except Exception as e:
#         print(f"Assistant evaluation error: {e}", file=sys.stderr)
#         raise

# def main(query_file):
#     try:
#         # Read query file
#         print(f"Reading query file: {query_file}", file=sys.stderr)
#         if not os.path.exists(query_file):
#             print(f"Error: Query file not found: {query_file}", file=sys.stderr)
#             sys.exit(1)
        
#         with open(query_file, 'r', encoding='utf-8') as f:
#             content = f.read()
#             print(f"Query file content: {content[:200]}...", file=sys.stderr)
#             job = json.loads(content)
        
#         # Validate job data
#         if not all(key in job for key in ['title', 'description', 'skills', 'budgetMin', 'budgetMax']):
#             print("Error: Invalid job data format", file=sys.stderr)
#             sys.exit(1)
        
#         # Create assistant and thread
#         assistant = create_assistant()
#         thread = client.beta.threads.create()
#         print(f"Created thread: {thread.id}", file=sys.stderr)
        
#         # Evaluate job
#         result = evaluate_job(assistant, None, job, thread)
        
#         # Output result
#         print(json.dumps(result))
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)

# if __name__ == '__main__':
#     if len(sys.argv) != 2:
#         print("Error: Expected query file path as argument", file=sys.stderr)
#         sys.exit(1)
#     query_file = sys.argv[1]
#     main(query_file)


# working by use of embeddings api and assistant api
# import sys
# import psycopg2
# from openai import OpenAI
# from dotenv import load_dotenv
# import os
# import json
# import numpy as np
# import re

# # Load environment variables
# load_dotenv()

# # Database configuration
# DB_CONFIG = {
#     'dbname': os.getenv('DB_NAME', 'profiledb'),
#     'user': os.getenv('DB_USER', 'profile'),
#     'password': os.getenv('DB_PASSWORD', 'profileUYh$13#'),
#     'host': os.getenv('DB_HOST', '122.176.158.168'),
#     'port': os.getenv('DB_PORT', '5432'),
#     'sslmode': 'require'
# }

# # Initialize OpenAI client
# client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# def cosine_similarity(a, b):
#     a = np.array(a)
#     b = np.array(b)
#     score = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
#     print(f"Calculated cosine similarity: {score}", file=sys.stderr)
#     return score

# def get_query_embedding(query_text):
#     try:
#         print(f"Generating embedding for query: {query_text[:50]}...", file=sys.stderr)
#         response = client.embeddings.create(
#             input=query_text,
#             model="text-embedding-ada-002"
#         )
#         embedding = response.data[0].embedding
#         print(f"Query embedding generated, length: {len(embedding)}", file=sys.stderr)
#         return embedding
#     except Exception as e:
#         print(f"Query embedding error: {e}", file=sys.stderr)
#         raise

# def create_assistant():
#     try:
#         assistant = client.beta.assistants.create(
#             name="n8n Automation Matcher",
#             instructions="You are an expert in evaluating job relevance for technical profiles. Given a job description and a candidate profile, assess the candidate's suitability. Provide a relevance score (0-100) and a detailed reason explaining the match, including relevant skills, experience, and any gaps. Format the response as: **Job Relevance Score: X**\n\n**Reason:**\n1. Point 1\n2. Point 2\n...",
#             model="gpt-4o-mini",
#             tools=[]  # No tools needed for this use case
#         )
#         print(f"Created assistant: {assistant.id}", file=sys.stderr)
#         return assistant
#     except Exception as e:
#         print(f"Assistant creation error: {e}", file=sys.stderr)
#         raise

# def evaluate_relevance(assistant, profile_content, query_text, thread):
#     try:
#         # Add profile and query to the thread
#         client.beta.threads.messages.create(
#             thread_id=thread.id,
#             role="user",
#             content=f"Profile: {profile_content}\nJob: {query_text}\nIs this job relevant? Provide a score (0-100) and reason."
#         )
        
#         # Run the assistant
#         run = client.beta.threads.runs.create(
#             thread_id=thread.id,
#             assistant_id=assistant.id
#         )
        
#         # Poll for completion
#         while run.status != "completed":
#             run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
#             print(f"Run status: {run.status}", file=sys.stderr)
        
#         # Retrieve messages
#         messages = client.beta.threads.messages.list(thread_id=thread.id)
#         response = messages.data[0].content[0].text.value
#         print(f"Assistant response: {response[:200]}...", file=sys.stderr)
#         return response
#     except Exception as e:
#         print(f"Assistant evaluation error: {e}", file=sys.stderr)
#         raise

# def main(query_file):
#     try:
#         # Read query file
#         print(f"Reading query file: {query_file}", file=sys.stderr)
#         if not os.path.exists(query_file):
#             print(f"Error: Query file not found: {query_file}", file=sys.stderr)
#             sys.exit(1)
        
#         with open(query_file, 'r', encoding='utf-8') as f:
#             content = f.read()
#             print(f"Query file content: {content[:200]}...", file=sys.stderr)
#             query = json.loads(content)
#         query_text = f"{query['title']} {query['description']} {' '.join(query['skills'])}"
#         print(f"Parsed query title: {query['title']}", file=sys.stderr)

#         # Generate query embedding
#         query_embedding = get_query_embedding(query_text)

#         # Connect to database
#         print("Connecting to database...", file=sys.stderr)
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         # Retrieve embeddings
#         cursor.execute("SELECT profile_id, chunk, embedding FROM embeddings")
#         embeddings = cursor.fetchall()
#         print(f"Retrieved {len(embeddings)} embeddings", file=sys.stderr)

#         best_match = None
#         highest_score = -1
#         best_profile_id = None

#         # Find best matching profile
#         for profile_id, chunk, embedding_json in embeddings:
#             print(f"Processing embedding for profile_id: {profile_id}, chunk: {chunk[:50]}...", file=sys.stderr)
#             try:
#                 if isinstance(embedding_json, str):
#                     embedding = json.loads(embedding_json)
#                 elif isinstance(embedding_json, list):
#                     embedding = embedding_json
#                 else:
#                     print(f"Error: Unexpected embedding type: {type(embedding_json)}", file=sys.stderr)
#                     continue

#                 if not isinstance(embedding, list) or not all(isinstance(x, (int, float)) for x in embedding):
#                     print(f"Error: Invalid embedding format for profile_id: {profile_id}", file=sys.stderr)
#                     continue

#                 score = cosine_similarity(query_embedding, embedding)
#                 print(f"Score for profile_id {profile_id}: {score}", file=sys.stderr)
#                 if score > highest_score:
#                     highest_score = score
#                     best_match = chunk
#                     best_profile_id = profile_id
#             except json.JSONDecodeError as e:
#                 print(f"JSON parsing error for embedding (profile_id: {profile_id}): {e}", file=sys.stderr)
#                 continue

#         if highest_score < 0.5:
#             result = {
#                 "relevance": "No",
#                 "score": int(highest_score * 100),
#                 "reason": "No sufficiently relevant profile found"
#             }
#             print(f"No relevant profile found, highest score: {highest_score}", file=sys.stderr)
#         else:
#             # Fetch profile details
#             cursor.execute(
#                 "SELECT name, content FROM profiles WHERE id = %s",
#                 (best_profile_id,)
#             )
#             profile = cursor.fetchone()
#             if not profile:
#                 print(f"Error: No profile found for profile_id: {best_profile_id}", file=sys.stderr)
#                 result = {
#                     "relevance": "No",
#                     "score": int(highest_score * 100),
#                     "reason": "Profile not found in database"
#                 }
#             else:
#                 profile_name, profile_content = profile
#                 print(f"Found profile: {profile_name}, content length: {len(profile_content)}", file=sys.stderr)

#                 # Create assistant and thread
#                 assistant = create_assistant()
#                 thread = client.beta.threads.create()
#                 print(f"Created thread: {thread.id}", file=sys.stderr)

#                 # Evaluate relevance using Assistant API
#                 gpt_response = evaluate_relevance(assistant, profile_content, query_text, thread)

#                 # Extract score from response
#                 score_match = re.search(r"Score: (\d+)", gpt_response)
#                 gpt_score = int(score_match.group(1)) if score_match else int(highest_score * 100)
                
#                 # Use cosine similarity score for consistency with original response
#                 result = {
#                     "relevance": "Yes",
#                     "score": int(highest_score * 100),  # 81
#                     "reason": gpt_response
#                 }
#                 print(f"Matched profile: {profile_name} with score: {int(highest_score * 100)}", file=sys.stderr)

#         # Output result
#         print(json.dumps(result))
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()
#         print("Database connection closed", file=sys.stderr)

# if __name__ == '__main__':
#     if len(sys.argv) != 2:
#         print("Error: Expected query file path as argument", file=sys.stderr)
#         sys.exit(1)
#     query_file = sys.argv[1]
#     main(query_file)

# with job poposal
#  working fine but without single assistand and thread
# import sys
# import psycopg2
# from openai import OpenAI
# from dotenv import load_dotenv
# import os
# import json
# import numpy as np
# import uuid

# # Load environment variables
# load_dotenv()

# # Database configuration
# DB_CONFIG = {
#     'dbname': os.getenv('DB_NAME', 'profiledb'),
#     'user': os.getenv('DB_USER', 'profile'),
#     'password': os.getenv('DB_PASSWORD', 'profileUYh$13#'),
#     'host': os.getenv('DB_HOST', '122.176.158.168'),
#     'port': os.getenv('DB_PORT', '5432'),  
#     'sslmode': 'require'
# }

# # Initialize OpenAI client
# client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# def cosine_similarity(a, b):
#     a = np.array(a)
#     b = np.array(b)
#     score = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
#     print(f"Calculated cosine similarity: {score}", file=sys.stderr)
#     return score

# def get_query_embedding(query_text):
#     try:
#         print(f"Generating embedding for query: {query_text[:200]}...", file=sys.stderr)
#         response = client.embeddings.create(
#             input=query_text,
#             model="text-embedding-ada-002"
#         )
#         embedding = response.data[0].embedding
#         print(f"Query embedding generated, length: {len(embedding)}", file=sys.stderr)
#         return embedding
#     except Exception as e:
#         print(f"Query embedding error: {e}", file=sys.stderr)
#         raise

# def create_assistant():
#     try:
#         assistant_id = str(uuid.uuid4())
#         assistant = client.beta.assistants.create(
#             name=assistant_id,
#             instructions="You are an expert in generating professional job proposals for technical roles, including full stack development, AI, automation, and project management. Given a job description and a candidate's profile, create a tailored job proposal in Markdown format. The proposal should include: (1) an introductory greeting addressing the hiring manager, (2) a section highlighting the candidate's relevant skills and experiences that align with the job requirements, (3) a proposed approach to deliver the job's key deliverables, addressing specific roles or tasks mentioned (e.g., full stack, AI, n8n), and (4) a closing statement expressing enthusiasm, availability, and a proposed rate within the job’s budget range. Use a professional yet engaging tone, and keep the proposal concise (500-600 words). Format as: # **Job Proposal for [Job Title]**\n\n**Dear Hiring Manager,**\n\n## **Why I’m a Strong Fit**\n...\n## **My Approach to Your Project**\n...\n## **Let’s Connect**\n...",
#             model="gpt-4o-mini",
#             tools=[]  # No tools needed
#         )
#         print(f"Created assistant: {assistant.id}", file=sys.stderr)
#         return assistant
#     except Exception as e:
#         print(f"Assistant creation error: {e}", file=sys.stderr)
#         raise

# def generate_proposal(assistant, profile_content, query_text, budget_min, budget_max, thread):
#     try:
#         # Add profile, query, and budget to the thread
#         client.beta.threads.messages.create(
#             thread_id=thread.id,
#             role="user",
#             content=f"Profile: {profile_content}\nJob: {query_text}\nBudget Range: ${budget_min}-${budget_max}\nGenerate a job proposal in Markdown format for this job, tailored to the candidate's profile."
#         )
        
#         # Run the assistant
#         run = client.beta.threads.runs.create(
#             thread_id=thread.id,
#             assistant_id=assistant.id
#         )
        
#         # Poll for completion
#         while run.status != "completed":
#             run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
#             print(f"Run status: {run.status}", file=sys.stderr)
        
#         # Retrieve messages
#         messages = client.beta.threads.messages.list(thread_id=thread.id)
#         response = messages.data[0].content[0].text.value
#         print(f"Assistant response: {response[:200]}...", file=sys.stderr)
#         return response
#     except Exception as e:
#         print(f"Proposal generation error: {e}", file=sys.stderr)
#         raise

# def main(query_file):
#     try:
#         # Read query file
#         print(f"Reading query file: {query_file}", file=sys.stderr)
#         if not os.path.exists(query_file):
#             print(f"Error: Query file not found: {query_file}", file=sys.stderr)
#             sys.exit(1)
        
#         with open(query_file, 'r', encoding='utf-8') as f:
#             content = f.read()
#             print(f"Query file content: {content[:200]}...", file=sys.stderr)
#             query = json.loads(content)
#         query_text = f"{query['title']} {query['description']} {' '.join(query.get('skills', []))}"
#         budget_min = query.get('budgetMin', 0)
#         budget_max = query.get('budgetMax', 1000)
#         print(f"Parsed query title: {query['title']}", file=sys.stderr)

#         # Generate query embedding
#         query_embedding = get_query_embedding(query_text)

#         # Connect to database
#         print("Connecting to database...", file=sys.stderr)
#         try:
#             conn = psycopg2.connect(**DB_CONFIG)
#         except Exception as e:
#             print(f"Database connection error: {e}", file=sys.stderr)
#             raise
#         cursor = conn.cursor()

#         # Retrieve embeddings
#         cursor.execute("SELECT profile_id, chunk, embedding FROM embeddings")
#         embeddings = cursor.fetchall()
#         print(f"Retrieved {len(embeddings)} embeddings", file=sys.stderr)

#         best_match = None
#         highest_score = -1
#         best_profile_id = None

#         # Find best matching profile
#         for profile_id, chunk, embedding_json in embeddings:
#             print(f"Processing embedding for profile_id: {profile_id}, chunk: {chunk[:50]}...", file=sys.stderr)
#             try:
#                 if isinstance(embedding_json, str):
#                     embedding = json.loads(embedding_json)
#                 elif isinstance(embedding_json, list):
#                     embedding = embedding_json
#                 else:
#                     print(f"Error: Unexpected embedding type: {type(embedding_json)}", file=sys.stderr)
#                     continue

#                 if not isinstance(embedding, list) or not all(isinstance(x, (int, float)) for x in embedding):
#                     print(f"Error: Invalid embedding format for profile_id: {profile_id}", file=sys.stderr)
#                     continue

#                 score = cosine_similarity(query_embedding, embedding)
#                 print(f"Score for profile_id {profile_id}: {score}", file=sys.stderr)
#                 if score > highest_score:
#                     highest_score = score
#                     best_match = chunk
#                     best_profile_id = profile_id
#             except json.JSONDecodeError as e:
#                 print(f"JSON parsing error for embedding (profile_id: {profile_id}): {e}", file=sys.stderr)
#                 continue

#         if highest_score < 0.5:
#             result = {
#                 "relevance": "No",
#                 "score": int(highest_score * 100),
#                 "proposal": "No sufficiently relevant profile found to generate a proposal."
#             }
#             print(f"No relevant profile found, highest score: {highest_score}", file=sys.stderr)
#         else:
#             # Fetch profile details
#             cursor.execute(
#                 "SELECT name, content FROM profiles WHERE id = %s",
#                 (best_profile_id,)
#             )
#             profile = cursor.fetchone()
#             if not profile:
#                 print(f"Error: No profile found for profile_id: {best_profile_id}", file=sys.stderr)
#                 result = {
#                     "relevance": "No",
#                     "score": int(highest_score * 100),
#                     "proposal": "Profile not found in database."
#                 }
#             else:
#                 profile_name, profile_content = profile
#                 print(f"Found profile: {profile_name}, content length: {len(profile_content)}", file=sys.stderr)

#                 # Create assistant and thread
#                 assistant = create_assistant()
#                 thread = client.beta.threads.create()
#                 print(f"Created thread: {thread.id}", file=sys.stderr)

#                 # Generate job proposal
#                 proposal = generate_proposal(assistant, profile_content, query_text, budget_min, budget_max, thread)

#                 result = {
#                     "relevance": "Yes",
#                     "score": int(highest_score * 100),
#                     "proposal": proposal
#                 }
#                 print(f"Generated proposal for profile: {profile_name} with score: {int(highest_score * 100)}", file=sys.stderr)

#         # Output result
#         print(json.dumps(result))
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()
#         print("Database connection closed", file=sys.stderr)

# if __name__ == '__main__':
#     if len(sys.argv) != 2:
#         print("Error: Expected query file path as argument", file=sys.stderr)
#         sys.exit(1)
#     query_file = sys.argv[1]
#     main(query_file)


#  working fine but with single assistand and thread and automatically creating assistant if not exists
import sys
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import uuid
import numpy as np

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'profiledb'),
    'user': os.getenv('DB_USER', 'profile'),
    'password': os.getenv('DB_PASSWORD', 'profileUYh$13#'),
    'host': os.getenv('DB_HOST', '122.176.158.168'),
    'port': os.getenv('DB_PORT', '5432'),
    'sslmode': 'require'
}

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def get_query_embedding(text):
    try:
        response = client.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        )
        embedding = response.data[0].embedding
        print(f"Query embedding generated, length: {len(embedding)}", file=sys.stderr)
        return embedding
    except Exception as e:
        print(f"Embedding generation error: {e}", file=sys.stderr)
        raise

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def get_assistant(assistant_id):
    try:
        assistant = client.beta.assistants.retrieve(assistant_id)
        print(f"Retrieved assistant: {assistant.id}", file=sys.stderr)
        return assistant
    except Exception as e:
        print(f"Assistant retrieval error: {e}", file=sys.stderr)
        raise

def generate_proposal(assistant, profile_content, query_text, budget_min, budget_max, thread, feedback=None):
    try:
        message_content = f"Profile: {profile_content}\nJob: {query_text}\nBudget Range: ${budget_min}-${budget_max}\n"
        if feedback:
            message_content += f"Feedback: {feedback}\n"
        message_content += "Generate a job proposal in Markdown format, tailored to the candidate's profile. Incorporate all feedback provided in the conversation history to improve the proposal, ensuring all suggestions are addressed."

        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=message_content
        )
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )
        while run.status != "completed":
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            print(f"Run status: {run.status}", file=sys.stderr)
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        response = messages.data[0].content[0].text.value
        print(f"Assistant response: {response[:200]}...", file=sys.stderr)
        return response
    except Exception as e:
        print(f"Proposal generation error: {e}", file=sys.stderr)
        raise

def store_feedback(cursor, feedback_id, profile_id, query_text, feedback, proposal, thread_id):
    try:
        cursor.execute(
            "INSERT INTO proposal_feedback (id, profile_id, query_text, feedback, proposal, thread_id, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, NOW())",
            (feedback_id, profile_id, query_text, feedback, proposal, thread_id)
        )
        print(f"Stored feedback ID: {feedback_id}", file=sys.stderr)
    except Exception as e:
        print(f"Feedback storage error: {e}", file=sys.stderr)
        raise

def main(query_file):
    try:
        # Read query file
        print(f"Reading query file: {query_file}", file=sys.stderr)
        if not os.path.exists(query_file):
            print(f"Error: Query file not found: {query_file}", file=sys.stderr)
            sys.exit(1)
        
        with open(query_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"Query file content: {content[:200]}...", file=sys.stderr)
            query = json.loads(content)
        query_text = f"{query['title']} {query['description']} {' '.join(query.get('skills', []))}"
        budget_min = query.get('budgetMin', 0)
        budget_max = query.get('budgetMax', 1000)
        feedback = query.get('feedback')
        thread_id = query.get('thread_id')
        assistant_id = query.get('assistantId')
        feedback_id = str(uuid.uuid4())
        if not assistant_id:
            print(f"Error: assistantId required", file=sys.stderr)
            sys.exit(1)
        print(f"Parsed query title: {query['title']}, feedback: {feedback[:50] if feedback else None}, thread_id: {thread_id}", file=sys.stderr)

        # Connect to database
        print("Connecting to database...", file=sys.stderr)
        try:
            conn = psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            print(f"Database connection error: {e}", file=sys.stderr)
            raise
        cursor = conn.cursor()

        # Get assistant
        assistant = get_assistant(assistant_id)

        if feedback and thread_id:
            # Refinement mode: use provided profile_id and thread
            profile_id = query.get('profile_id')
            if not profile_id:
                print(f"Error: profile_id required for refinement", file=sys.stderr)
                sys.exit(1)
            cursor.execute("SELECT name, content FROM profiles WHERE id = %s", (profile_id,))
            profile = cursor.fetchone()
            if not profile:
                result = {
                    "relevance": "No",
                    "score": 0,
                    "proposal": "Profile not found.",
                    "thread_id": thread_id
                }
                print(f"Error: No profile found for profile_id: {profile_id}", file=sys.stderr)
            else:
                profile_name, profile_content = profile
                if not profile_content:
                    result = {
                        "relevance": "No",
                        "score": 0,
                        "proposal": "No content available for the selected profile. Please upload a PDF.",
                        "thread_id": thread_id
                    }
                    print(f"Error: No content for profile: {profile_name}", file=sys.stderr)
                else:
                    print(f"Found profile: {profile_name}, content length: {len(profile_content)}", file=sys.stderr)
                    thread = client.beta.threads.retrieve(thread_id)
                    proposal = generate_proposal(assistant, profile_content, query_text, budget_min, budget_max, thread, feedback)
                    store_feedback(cursor, feedback_id, profile_id, query_text, feedback, proposal, thread_id)
                    conn.commit()
                    result = {
                        "relevance": "Yes",
                        "score": 100,
                        "proposal": proposal,
                        "profile_id": profile_id,
                        "profile_name": profile_name,
                        "thread_id": thread_id
                    }
                    print(f"Generated refined proposal for profile: {profile_name}", file=sys.stderr)
        else:
            # Initial mode: embedding-based matching
            print(f"Generating embedding for query: {query_text[:50]}...", file=sys.stderr)
            query_embedding = get_query_embedding(query_text)
            cursor.execute("SELECT profile_id, chunk, embedding FROM embeddings")
            embeddings = cursor.fetchall()
            print(f"Retrieved {len(embeddings)} embeddings", file=sys.stderr)

            best_match = None
            highest_score = -1
            best_profile_id = None

            for profile_id, chunk, embedding_json in embeddings:
                embedding = json.loads(embedding_json) if isinstance(embedding_json, str) else embedding_json
                score = cosine_similarity(query_embedding, embedding)
                print(f"Score for profile_id {profile_id}: {score}", file=sys.stderr)
                if score > highest_score:
                    highest_score = score
                    best_match = chunk
                    best_profile_id = profile_id

            if highest_score < 0.5 or not best_profile_id:
                result = {
                    "relevance": "No",
                    "score": int(highest_score * 100),
                    "proposal": "No sufficiently relevant profile found to generate a proposal.",
                    "thread_id": None
                }
                print(f"No relevant profile found, highest score: {highest_score}", file=sys.stderr)
            else:
                cursor.execute("SELECT name, content FROM profiles WHERE id = %s", (best_profile_id,))
                profile = cursor.fetchone()
                profile_name, profile_content = profile
                print(f"Found profile: {profile_name}, content length: {len(profile_content)}", file=sys.stderr)

                thread = client.beta.threads.create()
                print(f"Created thread: {thread.id}", file=sys.stderr)

                proposal = generate_proposal(assistant, profile_content, query_text, budget_min, budget_max, thread)
                store_feedback(cursor, feedback_id, best_profile_id, query_text, None, proposal, thread.id)
                conn.commit()
                result = {
                    "relevance": "Yes",
                    "score": int(highest_score * 100),
                    "proposal": proposal,
                    "profile_id": best_profile_id,
                    "profile_name": profile_name,
                    "thread_id": thread.id
                }
                print(f"Generated initial proposal for profile: {profile_name} with score: {int(highest_score * 100)}", file=sys.stderr)

        # Output result
        print(json.dumps(result))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        print("Database connection closed", file=sys.stderr)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Error: Expected query file path as argument", file=sys.stderr)
        sys.exit(1)
    query_file = sys.argv[1]
    main(query_file)