import sys
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import uuid
import numpy as np
import logging
from contextlib import contextmanager
from datetime import datetime

# Configure logging
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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

@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        yield conn
    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed")

def get_query_embedding(text):
    try:
        response = client.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        )
        embedding = response.data[0].embedding
        logging.info(f"Query embedding generated, length: {len(embedding)}")
        return embedding
    except Exception as e:
        logging.error(f"Embedding generation error: {e}")
        if "authentication" in str(e).lower():
            logging.error("Possible invalid API key or token")
        raise

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def get_assistant(assistant_id):
    try:
        assistant = client.beta.assistants.retrieve(assistant_id)
        logging.info(f"Retrieved assistant: {assistant.id}")
        return assistant
    except Exception as e:
        logging.error(f"Assistant retrieval error: {e}")
        if "not found" in str(e).lower():
            logging.error(f"Assistant ID {assistant_id} is invalid")
        raise

def generate_proposal(assistant, profile_content, query_text, budget_min, budget_max, thread, feedback=None):
    try:
        message_content = f"Profile: {profile_content}\nJob: {query_text}\nBudget Range: ${budget_min}-${budget_max}\n"
        if feedback:
            message_content += f"Feedback: {feedback}\n ascended"
        message_content += "Generate a job proposal in plain text format, tailored to the candidate's profile. Do not use any markdown symbols (e.g., #, *, **, -, >). Incorporate all feedback provided in the conversation history to improve the proposal, ensuring all suggestions are addressed."

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
            logging.info(f"Run status: {run.status}")
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        response = messages.data[0].content[0].text.value
        logging.info(f"Assistant response: {response[:200]}...")
        return response
    except Exception as e:
        logging.error(f"Proposal generation error: {e}")
        raise

def store_feedback(cursor, feedback_id, profile_id, query_text, feedback, proposal, thread_id, score):
    try:
        cursor.execute(
            "INSERT INTO proposal_feedback (id, profile_id, query_text, feedback, proposal, thread_id, score, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())",
            (feedback_id, profile_id, query_text, feedback, proposal, thread_id, score)
        )
        logging.info(f"Stored feedback ID: {feedback_id}")
    except Exception as e:
        logging.error(f"Feedback storage error: {e}")
        raise

def read_query_file(query_file):
    try:
        if not os.path.exists(query_file):
            logging.error(f"Query file not found: {query_file}")
            query_dir = os.path.dirname(query_file)
            if query_dir and os.path.exists(query_dir):
                logging.info(f"Directory contents: {os.listdir(query_dir)}")
            return None
        with open(query_file, 'r', encoding='utf-8') as f:
            content = f.read()
            logging.info(f"Query file content: {content[:200]}...")
            return json.loads(content)
    except Exception as e:
        logging.error(f"Error reading query file {query_file}: {e}")
        return None

def validate_query(query):
    required_fields = ['title', 'description']
    for field in required_fields:
        if field not in query:
            logging.error(f"Missing required field: {field}")
            return False
    return True

def main(query_file):
    try:
        query = read_query_file(query_file)
        if query is None or not validate_query(query):
            return {"error": f"Invalid or missing query file: {query_file}"}
        
        query_text_for_embedding = f"{query['title']} {query['description']} {' '.join(query.get('skills', []))}"
        query_text_for_storage = json.dumps(query['title'], ensure_ascii=False)
        budget_min = query.get('budgetMin', 0)
        budget_max = query.get('budgetMax', 1000)
        feedback = query.get('feedback')
        thread_id = query.get('thread_id')
        assistant_id = query.get('assistantId')
        feedback_id = str(uuid.uuid4())
        
        if not assistant_id:
            logging.error("Error: assistantId required")
            return {"error": "assistantId required"}

        logging.info(f"Parsed query title: {query['title']}, feedback: {feedback[:50] if feedback else None}, thread_id: {thread_id}")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            assistant = get_assistant(assistant_id)

            if feedback and thread_id:
                profile_id = query.get('profile_id')
                if not profile_id:
                    logging.error("Error: profile_id required for refinement")
                    return {"error": "profile_id required for refinement"}
                
                cursor.execute("SELECT name, content FROM profiles WHERE id = %s", (profile_id,))
                profile = cursor.fetchone()
                if not profile:
                    result = {
                        "relevance": "No",
                        "score": 0,
                        "proposal": "Profile not found.",
                        "thread_id": thread_id
                    }
                    logging.error(f"No profile found for profile_id: {profile_id}")
                else:
                    profile_name, profile_content = profile
                    if not profile_content:
                        result = {
                            "relevance": "No",
                            "score": 0,
                            "proposal": "No content available for the selected profile. Please upload a PDF.",
                            "thread_id": thread_id
                        }
                        logging.error(f"No content for profile: {profile_name}")
                    else:
                        logging.info(f"Found profile: {profile_name}, content length: {len(profile_content)}")
                        thread = client.beta.threads.retrieve(thread_id)
                        proposal = generate_proposal(assistant, profile_content, query_text_for_embedding, budget_min, budget_max, thread, feedback)
                        cursor.execute("SELECT score FROM proposal_feedback WHERE thread_id = %s ORDER BY created_at ASC LIMIT 1", (thread_id,))
                        initial_score = cursor.fetchone()
                        score = initial_score[0] if initial_score else 100
                        store_feedback(cursor, feedback_id, profile_id, query_text_for_storage, feedback, proposal, thread_id, score)
                        conn.commit()
                        result = {
                            "relevance": "Yes",
                            "score": score,
                            "proposal": proposal,
                            "profile_id": profile_id,
                            "profile_name": profile_name,
                            "thread_id": thread_id
                        }
                        logging.info(f"Generated refined proposal for profile: {profile_name}")
            else:
                logging.info(f"Generating embedding for query: {query_text_for_embedding[:50]}...")
                query_embedding = get_query_embedding(query_text_for_embedding)
                cursor.execute("SELECT profile_id, chunk, embedding FROM embeddings")
                embeddings = cursor.fetchall()
                logging.info(f"Retrieved {len(embeddings)} embeddings")

                best_match = None
                highest_score = -1
                best_profile_id = None
                relevant_chunks = []

                for profile_id, chunk, embedding_json in embeddings:
                    embedding = json.loads(embedding_json) if isinstance(embedding_json, str) else embedding_json
                    score = cosine_similarity(query_embedding, embedding)
                    logging.info(f"Score for profile_id {profile_id}: {score}")
                    if score > highest_score:
                        highest_score = score
                        best_match = chunk
                        best_profile_id = profile_id
                    if score > 0.7:
                        relevant_chunks.append(chunk)

                if highest_score < 0.5 or not best_profile_id:
                    result = {
                        "relevance": "No",
                        "score": int(highest_score * 100),
                        "proposal": "No sufficiently relevant profile found to generate a proposal.",
                        "thread_id": None
                    }
                    logging.info(f"No relevant profile found, highest score: {highest_score}")
                else:
                    cursor.execute("SELECT name, content FROM profiles WHERE id = %s", (best_profile_id,))
                    profile = cursor.fetchone()
                    profile_name, profile_content = profile
                    logging.info(f"Found profile: {profile_name}, content length: {len(profile_content)}")

                    combined_content = profile_content + '\n\n' + '\n'.join(relevant_chunks) if relevant_chunks else profile_content

                    thread = client.beta.threads.create()
                    logging.info(f"Created thread: {thread.id}")

                    proposal = generate_proposal(assistant, combined_content, query_text_for_embedding, budget_min, budget_max, thread)
                    store_feedback(cursor, feedback_id, best_profile_id, query_text_for_storage, None, proposal, thread.id, int(highest_score * 100))
                    conn.commit()
                    result = {
                        "relevance": "Yes",
                        "score": int(highest_score * 100),
                        "proposal": proposal,
                        "profile_id": best_profile_id,
                        "profile_name": profile_name,
                        "thread_id": thread.id
                    }
                    logging.info(f"Generated initial proposal for profile: {profile_name} with score: {int(highest_score * 100)}")

            if os.path.exists(query_file):
                os.remove(query_file)
                logging.info(f"Deleted query file: {query_file}")
            return result
    except Exception as e:
        logging.error(f"Error: {e}")
        return {"error": str(e)}

def process_query_files(query_files):
    results = []
    for query_file in query_files:
        logging.info(f"Processing query file: {query_file}")
        try:
            result = main(query_file)
            results.append(result)
        except Exception as e:
            logging.error(f"Failed to process {query_file}: {e}")
            results.append({"error": f"Failed to process {query_file}: {e}"})
    logging.info(f"Finished processing {len(query_files)} jobs")
    logging.info(f"Successful: {sum(1 for r in results if 'error' not in r)}")
    logging.info(f"Failed: {sum(1 for r in results if 'error' in r)}")
    return results

if __name__ == '__main__':
    if len(sys.argv) < 2:
        logging.error("Error: Expected at least one query file path as argument")
        sys.exit(1)
    query_files = sys.argv[1:]
    results = process_query_files(query_files)
    print(json.dumps(results))