from langchain_community.llms import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import ray
import time
import numpy as np
import PyPDF2
import uuid
import requests
from flask import jsonify
import json
import os
import uuid
from flask import jsonify
import requests
from database.db import get_db_connection, deduct_credits_from_user
from tika import parser as p


load_dotenv()
API_KEY = os.getenv('OPENAI_API_KEY')
embeddings = OpenAIEmbeddings(api_key=API_KEY)
sec_api_key = os.getenv('SEC_API_KEY')

# Embedding Configuration
EMBEDDING_MODEL = 'sentence-transformers/all-mpnet-base-v2'
EMBEDDING_DIMENSIONS = 768
MAX_CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200

# Global model cache for optimal performance
_embedding_model = None
_text_splitter = None
try:
    import threading
    _model_lock = threading.RLock()
    _splitter_lock = threading.RLock()
except ImportError:
    _model_lock = None
    _splitter_lock = None

## General for all chatbots
# Chat_type is an integer where 0=chatbot, 1=Edgar, 2=PDFUploader, etc
def add_chat_to_db(user_email, chat_type, model_type): #intake the current userID and the model type into the chat table
    conn, cursor = get_db_connection()

    cursor.execute("SELECT id FROM users WHERE email = %s", [user_email])
    user_id = cursor.fetchone()['id']

    cursor.execute('INSERT INTO chats (user_id, model_type, associated_task) VALUES (%s, %s, %s)', (user_id, model_type, chat_type))
    chat_id = cursor.lastrowid

    name = f"Chat {chat_id}"
    cursor.execute('UPDATE chats SET chat_name = %s WHERE id = %s', (name, chat_id))

    conn.commit()
    conn.close()

    return chat_id

def create_chat_shareable_url(chat_id):
    conn, cursor = get_db_connection()
    # Generate shareable UUID
    share_uuid = str(uuid.uuid4())
    # Insert into chat_shares
    cursor.execute(
        "INSERT INTO chat_shares (chat_id, share_uuid) VALUES (%s, %s)",
        (chat_id, share_uuid)
    )
    chat_share_id = cursor.lastrowid
    # Copy messages
    cursor.execute("""
        SELECT sent_from_user, message_text, created
        FROM messages
        WHERE chat_id = %s
        ORDER BY created ASC
    """, (chat_id,))
    messages = cursor.fetchall()
    for msg in messages:
        role = 'user' if msg['sent_from_user'] else 'chatbot'
        cursor.execute("""
            INSERT INTO chat_share_messages (chat_share_id, role, message_text, created)
            VALUES (%s, %s, %s, %s)
        """, (chat_share_id, role, msg['message_text'], msg['created']))
    # Copy documents
    cursor.execute("""
        SELECT id, document_name, document_text, storage_key, created
        FROM documents
        WHERE chat_id = %s
    """, (chat_id,))
    docs = cursor.fetchall()
    for doc in docs:
        cursor.execute("""
            INSERT INTO chat_share_documents (
                chat_share_id, document_name, document_text, storage_key, created
            ) VALUES (%s, %s, %s, %s, %s)
        """, (
            chat_share_id,
            doc["document_name"],
            doc["document_text"],
            doc["storage_key"],
            doc["created"]
        ))
        chat_share_doc_id = cursor.lastrowid
        # Copy chunks associated with the original document
        cursor.execute("""
            SELECT start_index, end_index, embedding_vector, page_number
            FROM chunks
            WHERE document_id = %s
        """, (doc["id"],))
        chunks = cursor.fetchall()
        for chunk in chunks:
            cursor.execute("""
                INSERT INTO chat_share_chunks (
                    chat_share_document_id, start_index, end_index, embedding_vector, page_number
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                chat_share_doc_id,
                chunk["start_index"],
                chunk["end_index"],
                chunk["embedding_vector"],
                chunk["page_number"]
            ))
    conn.commit()
    conn.close()
    return f"/playbook/{share_uuid}"

def access_sharable_chat(share_uuid, user_id=1):
    conn, cursor = get_db_connection()
    cursor.execute("SELECT * FROM chat_shares WHERE share_uuid = %s", (share_uuid,))
    share = cursor.fetchone()
    if not share:
        return jsonify({"error": "Snapshot not found"}), 404
    # Create new chat
    cursor.execute("""
        INSERT INTO chats (user_id, model_type, chat_name, associated_task)
        VALUES (%s, %s, %s, %s)
    """, (user_id, 0, "Imported from share", 0))
    new_chat_id = cursor.lastrowid
    # Copy messages
    cursor.execute("""
        SELECT role, message_text
        FROM chat_share_messages
        WHERE chat_share_id = %s
        ORDER BY created ASC
    """, (share['id'],))
    messages = cursor.fetchall()
    for msg in messages:
        sent_from_user = 1 if msg['role'] == 'user' else 0
        cursor.execute("""
            INSERT INTO messages (chat_id, message_text, sent_from_user)
            VALUES (%s, %s, %s)
        """, (new_chat_id, msg['message_text'], sent_from_user))
    # Copy documents + chunks
    cursor.execute("""
        SELECT id, document_name, document_text, storage_key
        FROM chat_share_documents
        WHERE chat_share_id = %s
    """, (share['id'],))
    docs = cursor.fetchall()
    for doc in docs:
        # Insert document
        cursor.execute("""
            INSERT INTO documents (chat_id, document_name, document_text, storage_key)
            VALUES (%s, NULL, %s, %s, %s)
        """, (new_chat_id, doc['document_name'], doc['document_text'], doc['storage_key']))
        new_doc_id = cursor.lastrowid
        # Retrieve and copy chunks from snapshot
        cursor.execute("""
            SELECT start_index, end_index, embedding_vector, page_number
            FROM chat_share_chunks
            WHERE chat_share_document_id = %s
        """, (doc['id'],))
        chunks = cursor.fetchall()
        for chunk in chunks:
            cursor.execute("""
                INSERT INTO chunks (
                    document_id, start_index, end_index, embedding_vector, page_number
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                new_doc_id,
                chunk['start_index'],
                chunk['end_index'],
                chunk['embedding_vector'],
                chunk['page_number']
            ))
    conn.commit()
    conn.close()
    return jsonify({"new_chat_id": new_chat_id})

## General for all chatbots
# Worflow_type is an integer where 2=FinancialReports

def update_chat_name_db(user_email, chat_id, new_name):
    conn, cursor = get_db_connection()

    query = """
    UPDATE chats
    JOIN users ON chats.user_id = users.id
    SET chats.chat_name = %s
    WHERE chats.id = %s AND users.email = %s;
    """
    cursor.execute(query, (new_name, chat_id, user_email))

    conn.commit()
    conn.close()

    return

def retrieve_chats_from_db(user_email):
    conn, cursor = get_db_connection()

    query = """
        SELECT chats.id, chats.model_type, chats.chat_name, chats.associated_task, chats.custom_model_key
        FROM chats
        JOIN users ON chats.user_id = users.id
        WHERE users.email = %s;
    """

    try:
        cursor.execute(query, (user_email,))
        chat_info = cursor.fetchall()

        # Force conversion to Python-native objects
        chat_info = [dict(row) for row in chat_info] if hasattr(cursor, "description") else chat_info

    finally:
        cursor.close()   # Always close cursor first
        conn.close()     # Then close connection
        # Removed conn.commit() – not needed for SELECT

    return chat_info

def find_most_recent_chat_from_db(user_email):
    conn, cursor = get_db_connection()

    query = """
        SELECT chats.id, chats.chat_name
        FROM chats
        JOIN users ON chats.user_id = users.id
        WHERE users.email = %s
        ORDER BY chats.created DESC
        LIMIT 1;
    """

    # Execute the query
    cursor.execute(query, [user_email])
    chat_info = cursor.fetchone()

    conn.commit()
    conn.close()

    return chat_info


def retrieve_message_from_db(user_email, chat_id, chat_type):
    conn, cursor = get_db_connection()

    query = """
        SELECT messages.created, chats.id, messages.id, messages.reasoning, messages.message_text, messages.sent_from_user, messages.relevant_chunks
        FROM messages
        JOIN chats ON messages.chat_id = chats.id
        JOIN users ON chats.user_id = users.id
        WHERE chats.id = %s AND users.email = %s AND chats.associated_task = %s;
        """

    # Execute the query
    cursor.execute(query, (chat_id, user_email, chat_type))
    messages = cursor.fetchall()

    conn.commit()
    conn.close()

    print("messages")

    # Process messages to parse reasoning JSON and format for frontend
    if messages:
        processed_messages = []
        for msg in messages:
            msg_dict = dict(msg)

            # Parse reasoning JSON if it exists
            if msg_dict.get('reasoning'):
                try:
                    reasoning_data = json.loads(msg_dict['reasoning'])
                    # Convert reasoning data to frontend format
                    if isinstance(reasoning_data, list):
                        # Already in array format
                        msg_dict['reasoning'] = reasoning_data
                    elif isinstance(reasoning_data, dict):
                        # Convert single reasoning object to array format
                        msg_dict['reasoning'] = [reasoning_data]
                    elif isinstance(reasoning_data, str):
                        # If it's a string, wrap it in a reasoning step object
                        msg_dict['reasoning'] = [{
                            'id': f'step-{msg_dict["id"]}',
                            'type': 'llm_reasoning',
                            'thought': reasoning_data,
                            'message': 'AI Reasoning',
                            'timestamp': int(time.time() * 1000)
                        }]
                    else:
                        msg_dict['reasoning'] = []

                    # Add the "complete" step that the frontend would have added during streaming
                    # This ensures consistency between streaming and reloaded messages
                    if msg_dict.get('reasoning') and msg_dict.get('sent_from_user') == 0:
                        # Extract the final thought from the last reasoning step if available
                        final_thought = None
                        for step in reversed(msg_dict['reasoning']):
                            if step.get('thought'):
                                final_thought = step['thought']
                                break

                        # If no thought found in reasoning steps, use part of the message text as thought
                        if not final_thought and msg_dict.get('message_text'):
                            # Use first 100 characters of the response as the thought
                            final_thought = msg_dict['message_text'][:100] + "..." if len(msg_dict['message_text']) > 100 else msg_dict['message_text']

                        complete_step = {
                            'id': f'step-complete-{msg_dict["id"]}',
                            'type': 'complete',
                            'thought': final_thought,
                            'message': 'Response complete',
                            'timestamp': int(time.time() * 1000)
                        }
                        msg_dict['reasoning'].append(complete_step)
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"Error parsing reasoning JSON for message {msg_dict.get('id')}: {e}")
                    msg_dict['reasoning'] = []
            else:
                msg_dict['reasoning'] = []

            processed_messages.append(msg_dict)

        return processed_messages

    return None if messages is None else messages

def delete_chat_from_db(chat_id, user_email):
    print("delete chat from db")
    conn, cursor = get_db_connection()

    delete_chunks_query = """
    DELETE chunks
    FROM chunks
    INNER JOIN documents ON chunks.document_id = documents.id
    INNER JOIN chats ON documents.chat_id = chats.id
    INNER JOIN users ON chats.user_id = users.id
    WHERE chats.id = %s AND users.email = %s;
    """
    cursor.execute(delete_chunks_query, (chat_id, user_email))

    delete_documents_query = """
    DELETE documents
    FROM documents
    INNER JOIN chats ON documents.chat_id = chats.id
    INNER JOIN users ON chats.user_id = users.id
    WHERE chats.id = %s AND users.email = %s;
    """
    cursor.execute(delete_documents_query, (chat_id, user_email))

    delete_messages_query = """
    DELETE messages
    FROM messages
    INNER JOIN chats ON messages.chat_id = chats.id
    INNER JOIN users ON chats.user_id = users.id
    WHERE chats.id = %s AND users.email = %s;
    """
    cursor.execute(delete_messages_query, (chat_id, user_email))

    query = """
    DELETE chats
    FROM chats
    INNER JOIN users ON chats.user_id = users.id
    WHERE chats.id = %s AND users.email = %s;
    """
    cursor.execute(query, (chat_id, user_email))

    conn.commit()

    if cursor.rowcount > 0:
        print(f"Deleted chat with ID {chat_id} for user {user_email}.")
        conn.close()
        cursor.close()
        return 'Successfully deleted'
    else:
        print(f"No chat deleted. Chat ID {chat_id} may not exist or does not belong to user {user_email}.")
        conn.close()
        cursor.close()
        return 'Could not delete'

def retrieve_messages_from_share_uuid(share_uuid):
    conn, cursor = get_db_connection()

    cursor.execute("""
        SELECT csm.role, csm.message_text, csm.created
        FROM chat_shares cs
        JOIN chat_share_messages csm ON cs.id = csm.chat_share_id
        WHERE cs.share_uuid = %s
        ORDER BY csm.created ASC
    """, (share_uuid,))

    messages = cursor.fetchall()

    conn.close()
    return messages

def get_document_content_from_db(id, email):
    conn, cursor = get_db_connection()

    # Query to get document content with user verification through chat ownership
    query = """
    SELECT d.document_text, d.document_name, d.id
    FROM documents d
    JOIN chats c ON d.chat_id = c.id
    JOIN users u ON c.user_id = u.id
    WHERE d.id = %s AND u.email = %s
    """

    cursor.execute(query, (id, email))
    document = cursor.fetchone()

    conn.close()
    cursor.close()

    if document:
        return {
            'id': document['id'],
            'document_name': document['document_name'],
            'document_text': document['document_text']
        }
    else:
        return None

def reset_chat_db(chat_id, user_email):
    print("reset chat")
    conn, cursor = get_db_connection()

    delete_messages_query = """
    DELETE messages
    FROM messages
    INNER JOIN chats ON messages.chat_id = chats.id
    INNER JOIN users ON chats.user_id = users.id
    WHERE chats.id = %s AND users.email = %s;
    """
    cursor.execute(delete_messages_query, (chat_id, user_email))

    conn.commit()

    if cursor.rowcount > 0:
        print(f"Deleted chat with ID {chat_id} for user {user_email}.")
        conn.close()
        cursor.close()
        return 'Successfully deleted'
    else:
        print(f"No chat deleted. Chat ID {chat_id} may not exist or does not belong to user {user_email}.")
        conn.close()
        cursor.close()
        return 'Could not delete'

def reset_uploaded_docs(chat_id, user_email):
    conn, cursor = get_db_connection()

    delete_chunks_query = """
    DELETE chunks
    FROM chunks
    INNER JOIN documents ON chunks.document_id = documents.id
    INNER JOIN chats ON documents.chat_id = chats.id
    INNER JOIN users ON chats.user_id = users.id
    WHERE chats.id = %s AND users.email = %s;
    """
    cursor.execute(delete_chunks_query, (chat_id, user_email))

    delete_documents_query = """
    DELETE documents
    FROM documents
    INNER JOIN chats ON documents.chat_id = chats.id
    INNER JOIN users ON chats.user_id = users.id
    WHERE chats.id = %s AND users.email = %s;
    """
    cursor.execute(delete_documents_query, (chat_id, user_email))

    conn.commit()

    conn.close()
    cursor.close()


def change_chat_mode_db(chat_mode_to_change_to, chat_id, user_email):
    conn, cursor = get_db_connection()

    query = """
    UPDATE chats
    JOIN users ON chats.user_id = users.id
    SET chats.model_type = %s
    WHERE chats.id = %s AND users.email = %s;
    """

    # Execute the query
    cursor.execute(query, (chat_mode_to_change_to, chat_id, user_email))

    conn.commit()
    conn.close()
    cursor.close()



def add_document_to_db(text, document_name, chat_id=None):
    if chat_id == 0:
        print(f"Guest session: Skipping database storage for document '{document_name}'")
        return None, False

    conn, cursor = get_db_connection()

    try:
        # Check if the document already exists for the given chat_id
        cursor.execute("""
            SELECT id, document_text
            FROM documents
            WHERE document_name = %s
            AND chat_id = %s
        """, (document_name, chat_id))
        existing_doc = cursor.fetchone()

        if existing_doc:
            existing_doc_id, existing_doc_text = existing_doc
            print(f"Document '{document_name}' already exists. Not creating a new entry.")
            return existing_doc_id, True  # Returning the ID of the existing document

        # If the document doesn't exist, create a new one
        storage_key = "temp"  # You can adjust how the storage key is generated
        cursor.execute("""
            INSERT INTO documents (document_text, document_name, storage_key, chat_id)
            VALUES (%s, %s, %s, %s)
        """, (text, document_name, storage_key, chat_id))

        doc_id = cursor.lastrowid

        conn.commit()
        return doc_id, False  # Returning the ID of the new document
    finally:
        cursor.close()
        conn.close()


@ray.remote
def chunk_document_by_page_optimized(text_pages, maxChunkSize, document_id):
    """
    Optimized page-based document chunking with RecursiveCharacterTextSplitter and batch embedding generation.
    Processes all chunks across all pages in batches for better performance and also preserving semantic boundaries so that the meaning is retained.
    """
    print("start optimized semantic page chunk doc")

    conn, cursor = get_db_connection()

    chunk_texts = []
    chunk_metadata = []
    globalStartIndex = 0
    page_number = 1

    try:
        # Get the global text splitter instance
        text_splitter = _get_text_splitter(maxChunkSize)

        # Process each page with semantic chunking
        for page_text in text_pages:
            # Split page text into semantic chunks
            page_chunks = text_splitter.split_text(page_text)
            print(f"Page {page_number}: Created {len(page_chunks)} semantic chunks")

            # Track position within this page for accurate indexing
            page_pos = 0
            for chunk in page_chunks:

                # Find chunk position in the page
                chunk_start_in_page = page_text.find(chunk, page_pos)
                if chunk_start_in_page == -1:
                    chunk_start_in_page = page_text.find(chunk)

                chunk_end_in_page = chunk_start_in_page + len(chunk)

                # Calculate global positions
                global_start = globalStartIndex + chunk_start_in_page
                global_end = globalStartIndex + chunk_end_in_page

                chunk_texts.append(chunk)
                chunk_metadata.append({
                    "global_start": global_start,
                    "global_end": global_end,
                    "page_number": page_number
                })

                # Update page position for next chunk search
                page_pos = chunk_start_in_page + 1

            globalStartIndex += len(page_text)
            page_number += 1

        # Generate embeddings for all chunks in batches
        print(f"Generating embeddings for {len(chunk_texts)} semantic page chunks in batches...")
        embeddings = get_embeddings_batch(chunk_texts, batch_size=32)

        # Validate dimensions
        for i, embedding in enumerate(embeddings):
            if len(embedding) != EMBEDDING_DIMENSIONS:
                raise RuntimeError(f"Page chunk {i} embedding dimension mismatch: expected {EMBEDDING_DIMENSIONS}, got {len(embedding)}")

        # Insert the chunks into database
        chunk_data = []
        for i, (metadata, embedding) in enumerate(zip(chunk_metadata, embeddings)):
            embedding_array = np.array(embedding)
            blob = embedding_array.tobytes()

            chunk_data.append((
                metadata["global_start"],
                metadata["global_end"],
                document_id,
                blob,
                metadata["page_number"]
            ))

        # Batch insert into database
        cursor.executemany(
            'INSERT INTO chunks (start_index, end_index, document_id, embedding_vector, page_number) VALUES (%s,%s,%s,%s,%s)',
            chunk_data
        )

        print(f"Successfully processed {len(chunk_data)} semantic page chunks with batch embeddings")
        conn.commit()

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[FATAL ERROR] Exception during optimized semantic page chunking: {e}")
        raise RuntimeError("Optimized semantic page chunking failed due to internal error")
    finally:
        conn.close()

@ray.remote
def chunk_document_by_page(text_pages, maxChunkSize, document_id):
    """
    Redirects to optimized version.
    """
    return chunk_document_by_page_optimized.remote(text_pages, maxChunkSize, document_id)

from openai import OpenAI
import threading

_embedding_model = None
_model_lock = threading.Lock()
EMBEDDING_MODEL = "text-embedding-3-small"  # or "text-embedding-3-large"
_client = OpenAI()

def _get_model():
    """
    Get a lightweight embedding model wrapper (OpenAI-based).
    Since OpenAI models are API-hosted, this just returns a callable.
    """
    global _embedding_model

    if _embedding_model:
        print("Skipping embedding model init")
        return _embedding_model

    with _model_lock:
        if _embedding_model is None:
            print(f"Using OpenAI embedding model: {EMBEDDING_MODEL}")

            def embed_fn(texts):
                """
                Generate embeddings for a list of strings.
                """
                if isinstance(texts, str):
                    texts = [texts]

                resp = _client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=texts
                )
                return [d.embedding for d in resp.data]

            _embedding_model = embed_fn

    return _embedding_model

# Dictionary to cache text splitters by chunk size
_text_splitters = {}

def _get_text_splitter(chunk_size=None):
    """
    Get a text splitter instance with thread-safe initialization.
    Caches splitters by chunk size to avoid recreating them and improve performance.

    Args:
        chunk_size (int, optional): Chunk size. Defaults to MAX_CHUNK_SIZE.

    Returns:
        RecursiveCharacterTextSplitter: The text splitter
    """
    global _text_splitters

    if chunk_size is None:
        chunk_size = MAX_CHUNK_SIZE

    if chunk_size not in _text_splitters:
        try:
            if _splitter_lock:
                with _splitter_lock:
                    if chunk_size not in _text_splitters:
                        print(f"Initializing RecursiveCharacterTextSplitter with chunk_size={chunk_size}...")
                        _text_splitters[chunk_size] = RecursiveCharacterTextSplitter(
                            chunk_size=chunk_size,
                            chunk_overlap=CHUNK_OVERLAP,
                            separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
                            length_function=len,
                        )
                        print(f"RecursiveCharacterTextSplitter (chunk_size={chunk_size}) initialized successfully!")
            else:
                print(f"Initializing RecursiveCharacterTextSplitter with chunk_size={chunk_size}...")
                _text_splitters[chunk_size] = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=CHUNK_OVERLAP,
                    separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
                    length_function=len,
                )
        except Exception as e:
            print(f"[ERROR] Failed to initialize text splitter: {e}")
            raise RuntimeError(f"Text splitter initialization failed: {str(e)}")

    return _text_splitters[chunk_size]

def preload_text_splitter():
    """
    Preload the text splitter to reduce latency on first use.
    Should be called during application startup for optimal performance.
    """
    try:
        print("Preloading RecursiveCharacterTextSplitter for faster document processing...")
        _get_text_splitter()
        print("RecursiveCharacterTextSplitter preloaded successfully!")
    except Exception as e:
        print(f"[WARNING] Failed to preload text splitter: {e}")

def preload_embedding_model():
    """
    Preload the embedding model to reduce latency on first use.
    Should be called during application startup for optimal performance.
    """
    try:
        print("Preloading embedding model for faster PDF processing...")
        _get_model()
        print("Embedding model preloaded successfully!")
    except Exception as e:
        print(f"[WARNING] Failed to preload embedding model: {e}")

def preload_models():
    """
    Preload both the embedding model and text splitter for optimal performance.
    Should be called during application startup.
    """
    preload_text_splitter()
    preload_embedding_model()

def get_embedding(question):
    """
    Get embedding for a given text using Multilingual-E5-large model.

    Args:
        question (str): The text to embed

    Returns:
        list: The embedding vector (1024 dimensions)

    Raises:
        RuntimeError: If the embedding generation fails
    """
    try:
        model = _get_model()

        # Add prefix for better performance as recommended by the model
        prefixed_question = f"query: {question}"
        embedding = model.encode(prefixed_question,  show_progress_bar=True, normalize_embeddings=True).tolist()

        # Validate dimensions using constant
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise RuntimeError(f"Unexpected embedding dimension: {len(embedding)}, expected {EMBEDDING_DIMENSIONS}")

        return embedding

    except Exception as e:
        print(f"[ERROR] Failed to get embedding: {e}")
        raise RuntimeError(f"Embedding generation failed: {str(e)}")

@ray.remote
def chunk_document(text, maxChunkSize, document_id):
    return chunk_document_optimized.remote(text, maxChunkSize, document_id)


def get_embeddings_batch(texts, batch_size=32):
    """
    Get embeddings for multiple texts in batches for better performance.

    Args:
        texts (list): List of text strings to embed
        batch_size (int): Number of texts to process in each batch (increased default)

    Returns:
        list: List of embedding vectors
    """
    try:
        import numpy as np
        model = _get_model()
        embeddings = []

        # Process texts in batches
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            # Add prefix for better performance as recommended by the model
            prefixed_texts = [f"passage: {text}" for text in batch_texts]

            # Get batch embeddings with optimized settings
            batch_embeddings = model.encode(
                prefixed_texts,
                normalize_embeddings=True,
                batch_size=batch_size,
                show_progress_bar=False,  # Reduce overhead
                convert_to_tensor=False   # Direct to list for efficiency
            )

            embeddings.extend(batch_embeddings.tolist())
            print(f"Processed batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")

        return embeddings

    except Exception as e:
        print(f"[ERROR] Failed to get batch embeddings: {e}")
        raise RuntimeError(f"Batch embedding generation failed: {str(e)}")

def prepare_chunks_for_embedding(text_pages, maxChunkSize):
    """
    Prepare semantic text chunks from pages using RecursiveCharacterTextSplitter without generating embeddings.
    This separates chunk preparation from embedding generation for optimization.

    Args:
        text_pages (list): List of page texts
        maxChunkSize (int): Maximum size for each chunk

    Returns:
        tuple: (chunk_texts, chunk_metadata) for batch processing
    """

    chunk_texts = []
    chunk_metadata = []
    globalStartIndex = 0
    page_number = 1

    # Get the global text splitter instance
    text_splitter = _get_text_splitter(maxChunkSize)

    for page_text in text_pages:
        # Split page text into semantic chunks
        page_chunks = text_splitter.split_text(page_text)

        # Track position within this page for accurate indexing
        page_position = 0
        for chunk in page_chunks:
            # Find chunk position within the page
            chunk_start_in_page = page_text.find(chunk, page_position)
            if chunk_start_in_page == -1:
                chunk_start_in_page = page_text.find(chunk)

            chunk_end_in_page = chunk_start_in_page + len(chunk)

            # Calculate global positions
            global_start = globalStartIndex + chunk_start_in_page
            global_end = globalStartIndex + chunk_end_in_page

            chunk_texts.append(chunk)
            chunk_metadata.append({
                "global_start": global_start,
                "global_end": global_end,
                "page_number": page_number
            })

            # Update page position for next chunk search
            page_position = chunk_start_in_page + 1

        globalStartIndex += len(page_text)
        page_number += 1

    return chunk_texts, chunk_metadata

def fast_pdf_ingestion(text_pages, maxChunkSize, document_id):
    """
    Fast PDF ingestion using RecursiveCharacterTextSplitter for semantic chunking and optimized batch embedding generation.
    This is the fastest way to process PDFs for embedding while preserving semantic boundaries.

    Args:
        text_pages (list): List of page texts from PDF
        maxChunkSize (int): Maximum chunk size
        document_id (int): Database document ID

    Returns:
        int: Number of chunks processed
    """
    print(f"Starting fast semantic PDF ingestion for document {document_id}")

    # Prepare all chunks using semantic chunking
    chunk_texts, chunk_metadata = prepare_chunks_for_embedding(text_pages, maxChunkSize)
    print(f"Prepared {len(chunk_texts)} semantic chunks for processing")

    # Generate all embeddings in optimized batches
    print("Generating embeddings in optimized batches...")
    embeddings = get_embeddings_batch(chunk_texts, batch_size=64)  # Larger batch for speed

    # Validate all embeddings
    for i, embedding in enumerate(embeddings):
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise RuntimeError(f"Chunk {i} embedding dimension mismatch: expected {EMBEDDING_DIMENSIONS}, got {len(embedding)}")

    # Batch insert to database
    conn, cursor = get_db_connection()
    try:
        chunk_data = []
        for metadata, embedding in zip(chunk_metadata, embeddings):
            embedding_array = np.array(embedding)
            blob = embedding_array.tobytes()

            chunk_data.append((
                metadata["global_start"],
                metadata["global_end"],
                document_id,
                blob,
                metadata["page_number"]
            ))

        # Single batch insert for maximum speed
        cursor.executemany(
            'INSERT INTO chunks (start_index, end_index, document_id, embedding_vector, page_number) VALUES (%s,%s,%s,%s,%s)',
            chunk_data
        )
        conn.commit()

        print(f"Fast semantic PDF ingestion completed: {len(chunk_data)} chunks processed")
        return len(chunk_data)

    except Exception as e:
        print(f"[ERROR] Fast semantic PDF ingestion failed: {e}")
        raise RuntimeError(f"Fast semantic PDF ingestion failed: {str(e)}")
    finally:
        conn.close()


@ray.remote
def chunk_document_optimized(text, maxChunkSize, document_id):
    """
    Chunk documents into smaller pieces with RecursiveCharacterTextSplitter and use optimized batch embedding creation.
    """

    conn, cursor = get_db_connection()

    chunk_texts = []
    chunk_metadata = []

    try:
        # Get the global text splitter instance for semantic-aware chunking
        text_splitter = _get_text_splitter(maxChunkSize)

        # Split text into semantic chunks
        chunks = text_splitter.split_text(text)
        print(f"RecursiveCharacterTextSplitter created {len(chunks)} semantic chunks")

        # Finding each chunk's positions in original text
        current_pos = 0
        for chunk in chunks:
            # Find chunk in the original text starting from current position
            chunk_start = text.find(chunk, current_pos)
            if chunk_start == -1:
                chunk_start = text.find(chunk)

            chunk_end = chunk_start + len(chunk)

            chunk_texts.append(chunk)
            chunk_metadata.append({
                "start_index": chunk_start,
                "end_index": chunk_end
            })

            # Update current position for next search
            current_pos = chunk_start + 1

        # Generate embeddings for all chunks in batches
        print(f"Generating embeddings for {len(chunk_texts)} semantic chunks in batches...")
        embeddings = get_embeddings_batch(chunk_texts, batch_size=32)

        # Make sure dimensions match
        for i, embedding in enumerate(embeddings):
            if len(embedding) != EMBEDDING_DIMENSIONS:
                raise RuntimeError(f"Chunk {i} embedding dimension mismatch: expected {EMBEDDING_DIMENSIONS}, got {len(embedding)}")

        # Insert all of the chunks into database
        chunk_data = []
        for i, (metadata, embedding) in enumerate(zip(chunk_metadata, embeddings)):
            embedding_array = np.array(embedding)
            blob = embedding_array.tobytes()

            chunk_data.append((
                metadata["start_index"],
                metadata["end_index"],
                document_id,
                blob
            ))

        # Batch insert into database
        cursor.executemany(
            'INSERT INTO chunks (start_index, end_index, document_id, embedding_vector) VALUES (%s,%s,%s,%s)',
            chunk_data
        )

        print(f"Successfully processed {len(chunk_data)} semantic chunks with batch embeddings")
        conn.commit()

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[FATAL ERROR] Exception during optimized semantic chunking: {e}")
        raise RuntimeError("Optimized semantic chunking failed due to internal error")
    finally:
        conn.close()


def knn(x, y):
    """
    Calculate k-nearest neighbors using cosine similarity.

    Args:
        x (np.array): Query vector (1D)
        y (np.array): Document vectors (2D: N x dimensions)

    Returns:
        list: Results sorted by similarity (best first)
    """
    # Ensure x is 2D: (1, dimensions)
    if x.ndim == 1:
        x = np.expand_dims(x, axis=0)

    # Ensure y is 2D: (N, dimensions)
    if y.ndim == 1:
        y = np.expand_dims(y, axis=0)

    # Validate dimensions match
    if x.shape[1] != y.shape[1]:
        raise ValueError(f"Dimension mismatch: query has {x.shape[1]} dims, documents have {y.shape[1]} dims")

    # Calculate cosine similarity with safety checks
    x_norm = np.linalg.norm(x, axis=1, keepdims=True)
    y_norm = np.linalg.norm(y, axis=1, keepdims=True)

    # Avoid division by zero
    x_norm = np.where(x_norm == 0, 1e-8, x_norm)
    y_norm = np.where(y_norm == 0, 1e-8, y_norm)

    # Normalize vectors
    x_normalized = x / x_norm
    y_normalized = y / y_norm

    # Calculate similarities
    similarities = np.dot(x_normalized, y_normalized.T).flatten()

    # Convert similarities to distances (lower is better)
    distances = 1 - similarities

    # Sort by similarity (best first)
    nearest_neighbors = np.argsort(distances)

    results = []
    for i in range(len(nearest_neighbors)):
        item = {
            "index": nearest_neighbors[i],
            "similarity_score": distances[nearest_neighbors[i]]
        }
        results.append(item)

    return results

def get_relevant_chunks(k: int, question: str, chat_id: int, user_email: str):
    conn, cursor = get_db_connection()

    #Fetch all document chunks with their embeddings for the given user and chat
    query = """
    SELECT c.start_index, c.end_index, c.embedding_vector, c.document_id, d.document_name, d.document_text
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    JOIN chats ch ON d.chat_id = ch.id
    JOIN users u ON ch.user_id = u.id
    WHERE u.email = %s AND ch.id = %s
    """
    cursor.execute(query, (user_email, chat_id))
    rows = cursor.fetchall()

    #Prepare chunk embeddings and metadata
    chunk_embeddings = []
    chunk_metadata = []
    for row in rows:
        embedding_blob = row["embedding_vector"]
        embedding = np.frombuffer(embedding_blob)

        if len(embedding) != EMBEDDING_DIMENSIONS:
            print(f"[WARNING] Skipping chunk with bad dimensions: {len(embedding)}")
            continue

        chunk_embeddings.append(embedding)
        chunk_metadata.append({
            "start": row["start_index"],
            "end": row["end_index"],
            "document_id": row["document_id"],
            "document_name": row["document_name"],
            "document_text": row["document_text"]
        })

    #Return early if no valid embeddings found
    if not chunk_embeddings:
        return []

    #Get embedding for the query
    try:
        query_embedding = np.array(get_embedding(question))
        if len(query_embedding) != EMBEDDING_DIMENSIONS:
            raise ValueError(f"Query embedding has wrong dimensions: {len(query_embedding)}")
    except Exception as e:
        print(f"[ERROR] Failed to generate query embedding: {e}")
        return []

    #Compute similarity and get top-k indices
    results = knn(query_embedding, np.array(chunk_embeddings))
    top_k = min(k, len(results))

    #Prepare result chunks
    source_chunks = []
    for i in range(top_k):
        idx = results[i]['index']
        meta = chunk_metadata[idx]
        chunk_text = meta["document_text"][meta["start"]:meta["end"]]
        document_name = meta["document_name"]
        source_chunks.append((chunk_text, document_name))

    return source_chunks


def add_sources_to_db(message_id, sources):
    combined_sources = ""

    print(f"DEBUG: sources type: {type(sources)}")
    print(f"DEBUG: sources content: {sources}")

    for i, source in enumerate(sources):
        print(f"DEBUG: source {i} type: {type(source)}")
        print(f"DEBUG: source {i} content: {source}")
        print(f"DEBUG: source {i} length: {len(source) if hasattr(source, '__len__') else 'no length'}")

        if len(source) >= 2:
            chunk_text, document_name = source[0], source[1]
        else:
            print(f"WARNING: Skipping malformed source {i}: {source}")
            continue

        combined_sources += f"Document: {document_name}: {chunk_text}\n\n"

    conn, cursor = get_db_connection()

    cursor.execute('UPDATE messages SET relevant_chunks = %s WHERE id = %s', (combined_sources, message_id))

    conn.commit()

    cursor.close()
    conn.close()

def add_wf_sources_to_db(prompt_id, sources):
    combined_sources = ""

    for source in sources:
        chunk_text, document_name = source
        combined_sources += f"Document: {document_name}: {chunk_text}\n\n"

    conn, cursor = get_db_connection()

    cursor.execute('UPDATE prompts SET relevant_chunks = %s WHERE id = %s', (combined_sources, prompt_id))

    conn.commit()

    cursor.close()
    conn.close()


def add_message_to_db(text, chat_id, isUser, reasoning=None):

    if chat_id == 0:
        return None #don't save guest messages
    #If isUser is 0, it is a bot message, 1 is a user message
    conn, cursor = get_db_connection()

    cursor.execute('INSERT INTO messages (message_text, chat_id, reasoning, sent_from_user) VALUES (%s,%s,%s, %s)', (text, chat_id, reasoning, isUser))
    message_id = cursor.lastrowid

    conn.commit()
    conn.close()
    cursor.close()

    return message_id

def add_prompt_to_db(prompt_text):
    conn, cursor = get_db_connection()

    cursor.execute('INSERT INTO prompts (prompt_text) VALUES (%s, %s)', (prompt_text))

    prompt_id = cursor.lastrowid

    conn.commit()
    conn.close()
    cursor.close()

    return prompt_id


def add_answer_to_db(answer, citation_id):
    conn, cursor = get_db_connection()

    # Insert the answer into the prompt_answers table
    cursor.execute(
        'INSERT INTO prompt_answers (prompt_id, citation_id, answer_text) VALUES (%s, %s, %s)',
        (citation_id, answer)
    )
    answer_id = cursor.lastrowid

    conn.commit()
    conn.close()
    cursor.close()

    return answer_id

def retrieve_docs_from_db(chat_id, user_email):
    conn, cursor = get_db_connection()

    query = """
        SELECT documents.document_name, documents.id
        FROM documents
        JOIN chats ON documents.chat_id = chats.id
        JOIN users ON chats.user_id = users.id
        WHERE chats.id = %s AND users.email = %s;
        """

    # Execute the query
    cursor.execute(query, (chat_id, user_email))
    docs = cursor.fetchall()

    conn.commit()
    conn.close()

    return docs

def delete_doc_from_db(doc_id, user_email):
    #Deletes the document and the associated chunks in the db
    conn, cursor = get_db_connection()

    verification_query = """
            SELECT d.id
            FROM documents d
            JOIN chats c ON d.chat_id = c.id
            JOIN users u ON c.user_id = u.id
            WHERE u.email = %s AND d.id = %s
        """
    cursor.execute(verification_query, (user_email, doc_id))
    verification_result = cursor.fetchone()

    if verification_result:
        delete_chunks_query = "DELETE FROM chunks WHERE document_id = %s"
        cursor.execute(delete_chunks_query, (doc_id,))
        delete_document_query = "DELETE FROM documents WHERE id = %s"
        cursor.execute(delete_document_query, (doc_id,))
        conn.commit()
    else:
        print("Document does not belong to the user or does not exist.")

    cursor.close()
    conn.close()

    return "success"

def add_model_key_to_db(model_key, chat_id, user_email):
    conn, cursor = get_db_connection()

    update_query = """
        UPDATE chats
        JOIN users ON chats.user_id = users.id
        SET chats.custom_model_key = %s
        WHERE chats.id = %s AND users.email = %s;
        """

    cursor.execute(update_query, (model_key, chat_id, user_email))

    conn.commit()


#specific to PDF reader
def get_text_from_single_file(file):
    reader = PyPDF2.PdfReader(file)
    text = ""

    for page_num in range(len(reader.pages)):

        text += reader.pages[page_num].extract_text()

    return text

def get_text_pages_from_single_file(file):
    reader = PyPDF2.PdfReader(file)
    pages_text = []

    for page_num in range(len(reader.pages)):
        page_text = reader.pages[page_num].extract_text()
        pages_text.append(page_text)


    return pages_text #text



#for the demo
def ensure_demo_user_exists(user_email):
    conn, cursor = get_db_connection()

    cursor.execute("SELECT id FROM users WHERE email = %s", (user_email,))
    result = cursor.fetchone()
    if result:
        return result['id']  # Assuming 'id' is the column name for user ID
    else:
        # Insert demo user
        insert_query = """
        INSERT INTO users (email, person_name, profile_pic_url, credits)
        VALUES (%s, 'Demo User', 'url_to_default_image', 0)
        """
        cursor.execute(insert_query, (user_email,))
        conn.commit()
        return cursor.lastrowid  # Return the newly created user ID

#For the SDK
def ensure_SDK_user_exists(user_email):
    conn, cursor = get_db_connection()

    cursor.execute("SELECT id FROM users WHERE email = %s", (user_email,))
    result = cursor.fetchone()
    if result:
        return result['id']  # Assuming 'id' is the column name for user ID
    else:
        # Insert SDK user with some initial credits for testing
        # NOTE: In production, you might want to set this to 0 and require users to purchase credits
        initial_credits = 0  # Give new SDK users 10 credits to start
        insert_query = """
        INSERT INTO users (email, person_name, profile_pic_url, credits)
        VALUES (%s, 'SDK User', 'url_to_default_image', %s)
        """
        cursor.execute(insert_query, (user_email, initial_credits))
        conn.commit()
        return cursor.lastrowid  # Return the newly created user ID

def get_chat_info(chat_id):
    conn, cursor = get_db_connection()

    cursor.execute("SELECT model_type, chat_name, associated_task FROM chats WHERE id = %s", (chat_id,))
    result = cursor.fetchone()

    if result:
        model_type = result['model_type']
        associated_task = result['associated_task'],
        chat_name = result['chat_name']
    else:
        model_type, associated_task, chat_name = None, None, None
    cursor.close()
    conn.close()

    return model_type, associated_task, chat_name

def get_message_info(answer_id, user_email):
    conn, cursor = get_db_connection()

    # Query to get the answer message and verify it belongs to the specified user by email
    answer_query = """
    SELECT m.*, c.id as chunk_id, c.start_index, c.end_index, c.page_number
    FROM messages m
    JOIN chats ct ON m.chat_id = ct.id
    JOIN users u ON ct.user_id = u.id
    LEFT JOIN chunks c ON FIND_IN_SET(c.id, m.relevant_chunks) > 0
    WHERE m.id = %s AND u.email = %s
    """

    cursor.execute(answer_query, (answer_id, user_email))
    answer_data = cursor.fetchall()

    if not answer_data:
        print("Either the answer does not exist or it doesn't belong to the specified user.")
        return None, None, None

    answer = answer_data[0]
    #chunks = answer_data[0]['chunk_id'] and [{
    #    'id': chunk['chunk_id'],
    #    'start_index': chunk['start_index'],
    #    'end_index': chunk['end_index'],
    #    'page_number': chunk['page_number']
    #} for chunk in answer_data if chunk['chunk_id']] or []

    # Query to find the previous message (question) in the same chat, sent from the user
    question_query = """
    SELECT m.*
    FROM messages m
    WHERE m.id < %s AND m.chat_id = %s AND m.sent_from_user = 1
    ORDER BY m.id DESC
    LIMIT 1
    """

    cursor.execute(question_query, (answer_id, answer['chat_id']))
    question = cursor.fetchone()

    cursor.close()
    return question, answer

def get_text_from_url(web_url):
    response = requests.get(web_url)
    result = p.from_buffer(response.content)
    text = result["content"].strip()
    text = text.replace("\n", "").replace("\t", "")
    #text = "".join(text)
    return text