
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