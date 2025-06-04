# after assistant api
# import sys
# import psycopg2
# from openai import OpenAI
# from dotenv import load_dotenv
# import os
# import json
# import uuid
# from datetime import datetime

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

# def chunk_text(text, max_length=500):
#     words = text.split()
#     chunks = []
#     current_chunk = []
#     current_length = 0

#     for word in words:
#         word_length = len(word) + 1
#         if current_length + word_length > max_length:
#             chunks.append(' '.join(current_chunk))
#             current_chunk = [word]
#             current_length = word_length
#         else:
#             current_chunk.append(word)
#             current_length += word_length

#     if current_chunk:
#         chunks.append(' '.join(current_chunk))
#     return chunks

# def generate_embeddings(text_chunks):
#     try:
#         embeddings = []
#         for chunk in text_chunks:
#             response = client.embeddings.create(
#                 input=chunk,
#                 model="text-embedding-ada-002"
#             )
#             embeddings.append(response.data[0].embedding)
#         print(f"Generated {len(embeddings)} embeddings", file=sys.stderr)
#         return embeddings
#     except Exception as e:
#         print(f"Embedding error: {e}", file=sys.stderr)
#         raise

# def create_assistant(profile_name):
#     try:
#         assistant = client.beta.assistants.create(
#             name=f"{profile_name} Assistant",
#             model="gpt-4o-mini",
#             instructions="You are an assistant that evaluates job relevance based on profile data."
#         )
#         print(f"Created assistant: {assistant.name}", file=sys.stderr)
#         return assistant.id
#     except Exception as e:
#         print(f"Assistant creation error: {e}", file=sys.stderr)
#         raise

# def main(profile_id, content, filename):
#     try:
#         # Validate UUID
#         try:
#             uuid_obj = uuid.UUID(profile_id)
#         except ValueError:
#             print(f"Invalid UUID: {profile_id}", file=sys.stderr)
#             sys.exit(1)

#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         # Verify profile exists
#         cursor.execute("SELECT name FROM profiles WHERE id = %s", (profile_id,))
#         result = cursor.fetchone()
#         if not result:
#             print(f"No profile found for ID: {profile_id}", file=sys.stderr)
#             sys.exit(1)
#         profile_name = result[0]
#         print(f"Found profile: {profile_name}", file=sys.stderr)

#         # Update profile
#         training_file_data = {
#             "filename": filename,
#             "uploaded_at": datetime.utcnow().isoformat()
#         }
#         cursor.execute(
#             """
#             UPDATE profiles
#             SET content = %s,
#                 training_file = %s,
#                 last_updated = CURRENT_TIMESTAMP,
#                 assistant_name = %s
#             WHERE id = %s
#             """,
#             (content, json.dumps(training_file_data), f"{profile_name} Assistant", profile_id)
#         )
#         print(f"Updated profile_id: {profile_id} with content, training_file, last_updated, assistant_name", file=sys.stderr)

#         # Generate and store embeddings
#         text_chunks = chunk_text(content)
#         print(f"Created {len(text_chunks)} text chunks", file=sys.stderr)
#         embeddings = generate_embeddings(text_chunks)
        
#         for i, (chunk, embedding) in enumerate(zip(text_chunks, embeddings)):
#             cursor.execute(
#                 """
#                 INSERT INTO embeddings (profile_id, chunk, embedding)
#                 VALUES (%s, %s, %s)
#                 """,
#                 (profile_id, chunk, json.dumps(embedding))
#             )
#             print(f"Inserted embedding {i+1}/{len(text_chunks)}", file=sys.stderr)

#         conn.commit()
#         print(f"Profile {profile_id} trained successfully", file=sys.stderr)
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         if 'conn' in locals():
#             conn.rollback()
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) != 4:
#         print("Error: Expected profile_id, content, and filename as arguments", file=sys.stderr)
#         sys.exit(1)
#     profile_id = sys.argv[1]
#     content = sys.argv[2]
#     filename = sys.argv[3]
#     main(profile_id, content, filename)



# import sys
# import psycopg2
# from openai import OpenAI
# from dotenv import load_dotenv
# import os
# import json
# import uuid
# from datetime import datetime

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

# def chunk_text(text, max_length=500):
#     words = text.split()
#     chunks = []
#     current_chunk = []
#     current_length = 0

#     for word in words:
#         word_length = len(word) + 1
#         if current_length + word_length > max_length:
#             chunks.append(' '.join(current_chunk))
#             current_chunk = [word]
#             current_length = word_length
#         else:
#             current_chunk.append(word)
#             current_length += word_length

#     if current_chunk:
#         chunks.append(' '.join(current_chunk))
#     return chunks

# def generate_embeddings(text_chunks):
#     try:
#         embeddings = []
#         for chunk in text_chunks:
#             response = client.embeddings.create(
#                 input=chunk,
#                 model="text-embedding-ada-002"
#             )
#             embeddings.append(response.data[0].embedding)
#         print(f"Generated {len(embeddings)} embeddings", file=sys.stderr)
#         return embeddings
#     except Exception as e:
#         print(f"Embedding error: {e}", file=sys.stderr)
#         raise

# def create_assistant(profile_name):
#     try:
#         assistant = client.beta.assistants.create(
#             name=f"{profile_name} Assistant",
#             model="gpt-4o-mini",
#             instructions="You are an assistant that evaluates job relevance based on profile data."
#         )
#         print(f"Created assistant: {assistant.name}", file=sys.stderr)
#         return assistant.id
#     except Exception as e:
#         print(f"Assistant creation error: {e}", file=sys.stderr)
#         raise

# def main(profile_id, content_file, filename):
#     try:
#         # Validate UUID
#         try:
#             uuid_obj = uuid.UUID(profile_id)
#         except ValueError:
#             print(f"Invalid UUID: {profile_id}", file=sys.stderr)
#             sys.exit(1)

#         # Read content from file
#         with open(content_file, 'r', encoding='utf-8') as f:
#             content = f.read()
#         print(f"Read content from {content_file}, length: {len(content)} characters", file=sys.stderr)

#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         # Verify profile exists
#         cursor.execute("SELECT name FROM profiles WHERE id = %s", (profile_id,))
#         result = cursor.fetchone()
#         if not result:
#             print(f"No profile found for ID: {profile_id}", file=sys.stderr)
#             sys.exit(1)
#         profile_name = result[0]
#         print(f"Found profile: {profile_name}", file=sys.stderr)

#         # Update profile
#         training_file_data = {
#             "filename": filename,
#             "uploaded_at": datetime.utcnow().isoformat()
#         }
#         cursor.execute(
#             """
#             UPDATE profiles
#             SET content = %s,
#                 training_file = %s,
#                 last_updated = CURRENT_TIMESTAMP,
#                 assistant_name = %s
#             WHERE id = %s
#             """,
#             (content, json.dumps(training_file_data), f"{profile_name} Assistant", profile_id)
#         )
#         print(f"Updated profile_id: {profile_id} with content, training_file, last_updated, assistant_name", file=sys.stderr)

#         # Generate and store embeddings
#         text_chunks = chunk_text(content)
#         print(f"Created {len(text_chunks)} text chunks", file=sys.stderr)
#         embeddings = generate_embeddings(text_chunks)
        
#         for i, (chunk, embedding) in enumerate(zip(text_chunks, embeddings)):
#             cursor.execute(
#                 """
#                 INSERT INTO embeddings (profile_id, chunk, embedding)
#                 VALUES (%s, %s, %s)
#                 """,
#                 (profile_id, chunk, json.dumps(embedding))
#             )
#             print(f"Inserted embedding {i+1}/{len(text_chunks)}", file=sys.stderr)

#         conn.commit()
#         print(f"Profile {profile_id} trained successfully", file=sys.stderr)
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         if 'conn' in locals():
#             conn.rollback()
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) != 4:
#         print("Error: Expected profile_id, content_file, and filename as arguments", file=sys.stderr)
#         sys.exit(1)
#     profile_id = sys.argv[1]
#     content_file = sys.argv[2]
#     filename = sys.argv[3]
#     main(profile_id, content_file, filename)


# import sys
# import psycopg2
# from openai import OpenAI
# from dotenv import load_dotenv
# import os
# import json
# import uuid
# from datetime import datetime, timezone

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

# def chunk_text(text, max_length=500):
#     words = text.split()
#     chunks = []
#     current_chunk = []
#     current_length = 0

#     for word in words:
#         word_length = len(word) + 1
#         if current_length + word_length > max_length:
#             chunks.append(' '.join(current_chunk))
#             current_chunk = [word]
#             current_length = word_length
#         else:
#             current_chunk.append(word)
#             current_length += word_length

#     if current_chunk:
#         chunks.append(' '.join(current_chunk))
#     return chunks

# def generate_embeddings(text_chunks):
#     try:
#         embeddings = []
#         for chunk in text_chunks:
#             response = client.embeddings.create(
#                 input=chunk,
#                 model="text-embedding-ada-002"
#             )
#             embeddings.append(response.data[0].embedding)
#         print(f"Generated {len(embeddings)} embeddings")
#         return embeddings
#     except Exception as e:
#         print(f"Embedding error: {e}", file=sys.stderr)
#         raise

# def create_assistant(profile_name):
#     try:
#         assistant = client.beta.assistants.create(
#             name=f"{profile_name} Assistant",
#             model="gpt-4o-mini",
#             instructions="You are an assistant that evaluates job relevance based on profile data."
#         )
#         print(f"Created assistant: {assistant.name}")
#         return assistant.id
#     except Exception as e:
#         print(f"Assistant creation error: {e}", file=sys.stderr)
#         raise

# def main(profile_id, content_file, filename):
#     try:
#         # Validate UUID
#         try:
#             uuid_obj = uuid.UUID(profile_id)
#         except ValueError:
#             print(f"Invalid UUID: {profile_id}", file=sys.stderr)
#             sys.exit(1)

#         # Read content from file
#         with open(content_file, 'r', encoding='utf-8') as f:
#             content = f.read()
#         print(f"Read content from {content_file}, length: {len(content)} characters")

#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()

#         # Verify profile exists
#         cursor.execute("SELECT name FROM profiles WHERE id = %s", (profile_id,))
#         result = cursor.fetchone()
#         if not result:
#             print(f"No profile found for ID: {profile_id}", file=sys.stderr)
#             sys.exit(1)
#         profile_name = result[0]
#         print(f"Found profile: {profile_name}")

#         # Update profile
#         training_file_data = {
#             "filename": filename,
#             "uploaded_at": datetime.now(timezone.utc).isoformat()
#         }
#         cursor.execute(
#             """
#             UPDATE profiles
#             SET content = %s,
#                 training_file = %s,
#                 last_updated = CURRENT_TIMESTAMP,
#                 assistant_name = %s
#             WHERE id = %s
#             """,
#             (content, json.dumps(training_file_data), f"{profile_name} Assistant", profile_id)
#         )
#         print(f"Updated profile_id: {profile_id} with content, training_file, last_updated, assistant_name")

#         # Generate and store embeddings
#         text_chunks = chunk_text(content)
#         print(f"Created {len(text_chunks)} text chunks")
#         embeddings = generate_embeddings(text_chunks)
        
#         for i, (chunk, embedding) in enumerate(zip(text_chunks, embeddings)):
#             cursor.execute(
#                 """
#                 INSERT INTO embeddings (profile_id, chunk, embedding)
#                 VALUES (%s, %s, %s)
#                 """,
#                 (profile_id, chunk, json.dumps(embedding))
#             )
#             print(f"Inserted embedding {i+1}/{len(text_chunks)}")

#         conn.commit()
#         print(f"Profile {profile_id} trained successfully")
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
#         if 'conn' in locals():
#             conn.rollback()
#         sys.exit(1)
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'conn' in locals():
#             conn.close()

# if __name__ == '__main__':
#     if len(sys.argv) != 4:
#         print("Error: Expected profile_id, content_file, and filename as arguments", file=sys.stderr)
#         sys.exit(1)
#     profile_id = sys.argv[1]
#     content_file = sys.argv[2]
#     filename = sys.argv[3]
#     main(profile_id, content_file, filename)

import sys
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import uuid
from datetime import datetime, timezone

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

def chunk_text(text, max_length=500):
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0

    for word in words:
        word_length = len(word) + 1
        if current_length + word_length > max_length:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = word_length
        else:
            current_chunk.append(word)
            current_length += word_length

    if current_chunk:
        chunks.append(' '.join(current_chunk))
    return chunks

def generate_embeddings(text_chunks):
    try:
        embeddings = []
        for chunk in text_chunks:
            response = client.embeddings.create(
                input=chunk,
                model="text-embedding-ada-002"
            )
            embeddings.append(response.data[0].embedding)
        print(f"Generated {len(embeddings)} embeddings")
        return embeddings
    except Exception as e:
        print(f"Embedding error: {e}", file=sys.stderr)
        raise

def main(profile_id, content_file, filename):
    try:
        # Validate UUID
        try:
            uuid_obj = uuid.UUID(profile_id)
        except ValueError:
            print(f"Invalid UUID: {profile_id}", file=sys.stderr)
            sys.exit(1)

        # Read content from file
        with open(content_file, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"Read content from {content_file}, length: {len(content)} characters")

        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Verify profile exists
        cursor.execute("SELECT name FROM profiles WHERE id = %s", (profile_id,))
        result = cursor.fetchone()
        if not result:
            print(f"No profile found for ID: {profile_id}", file=sys.stderr)
            sys.exit(1)
        profile_name = result[0]
        print(f"Found profile: {profile_name}")

        # Update profile (only content and assistant_name, preserve training_file)
        cursor.execute(
            """
            UPDATE profiles
            SET content = %s,
                assistant_name = %s,
                last_updated = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (content, f"{profile_name} Assistant", profile_id)
        )
        print(f"Updated profile_id: {profile_id} with content, assistant_name, last_updated")

        # Generate and store embeddings
        text_chunks = chunk_text(content)
        print(f"Created {len(text_chunks)} text chunks")
        embeddings = generate_embeddings(text_chunks)
        
        for i, (chunk, embedding) in enumerate(zip(text_chunks, embeddings)):
            cursor.execute(
                """
                INSERT INTO embeddings (profile_id, chunk, embedding)
                VALUES (%s, %s, %s)
                """,
                (profile_id, chunk, json.dumps(embedding))
            )
            print(f"Inserted embedding {i+1}/{len(text_chunks)}")

        conn.commit()
        print(f"Profile {profile_id} trained successfully")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if 'conn' in locals():
            conn.rollback()
        sys.exit(1)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Error: Expected profile_id, content_file, and filename as arguments", file=sys.stderr)
        sys.exit(1)
    profile_id = sys.argv[1]
    content_file = sys.argv[2]
    filename = sys.argv[3]
    main(profile_id, content_file, filename)