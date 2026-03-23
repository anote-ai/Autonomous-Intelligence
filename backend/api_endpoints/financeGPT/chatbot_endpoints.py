import json
import os
import time

import numpy as np
import PyPDF2
import ray
import requests
from dotenv import load_dotenv
from flask import jsonify
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.llms import OpenAI
from langchain_openai import OpenAIEmbeddings
from database.db import (
    add_chat,
    add_chunks,
    add_chunks_with_page_numbers,
    add_document,
    add_message,
    add_model_key,
    add_prompt,
    add_prompt_answer,
    add_sources_to_message,
    add_sources_to_prompt,
    access_shareable_chat,
    change_chat_mode,
    create_chat_shareable_url as create_shareable_url,
    delete_chat,
    delete_doc,
    ensure_demo_user_exists as ensure_demo_user,
    ensure_sdk_user_exists as ensure_sdk_user,
    find_most_recent_chat,
    get_chat_info as fetch_chat_info,
    get_chat_chunks,
    get_document_content,
    get_db_connection,
    get_message_info as fetch_message_info,
    reset_chat,
    reset_uploaded_docs as clear_uploaded_docs,
    retrieve_messages_from_share_uuid as fetch_messages_from_share_uuid,
    retrieve_chats,
    retrieve_docs,
    retrieve_messages,
    update_chat_name,
)
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
    return add_chat(user_email, chat_type, model_type)

def create_chat_shareable_url(chat_id):
    return create_shareable_url(chat_id)

def access_sharable_chat(share_uuid, user_id=1):
    new_chat_id = access_shareable_chat(share_uuid, user_id)
    if new_chat_id is None:
        return jsonify({"error": "Snapshot not found"}), 404
    return jsonify({"new_chat_id": new_chat_id})

## General for all chatbots
# Worflow_type is an integer where 2=FinancialReports

def update_chat_name_db(user_email, chat_id, new_name):
    return update_chat_name(user_email, chat_id, new_name)

def retrieve_chats_from_db(user_email):
    return retrieve_chats(user_email)

def find_most_recent_chat_from_db(user_email):
    return find_most_recent_chat(user_email)


def retrieve_message_from_db(user_email, chat_id, chat_type):
    return retrieve_messages(user_email, chat_id, chat_type)

def delete_chat_from_db(chat_id, user_email):
    return delete_chat(chat_id, user_email)

def retrieve_messages_from_share_uuid(share_uuid):
    return fetch_messages_from_share_uuid(share_uuid)

def get_document_content_from_db(id, email):
    return get_document_content(id, email)

def reset_chat_db(chat_id, user_email):
    return reset_chat(chat_id, user_email)

def reset_uploaded_docs(chat_id, user_email):
    return clear_uploaded_docs(chat_id, user_email)


def change_chat_mode_db(chat_mode_to_change_to, chat_id, user_email):
    return change_chat_mode(chat_mode_to_change_to, chat_id, user_email)



def add_document_to_db(text, document_name, chat_id=None):
    return add_document(text, document_name, chat_id)


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
        for metadata, embedding in zip(chunk_metadata, embeddings, strict=False):
            embedding_array = np.array(embedding)
            blob = embedding_array.tobytes()

            chunk_data.append((
                metadata["global_start"],
                metadata["global_end"],
                document_id,
                blob,
                metadata["page_number"]
            ))

        add_chunks_with_page_numbers(chunk_data)

        print(f"Successfully processed {len(chunk_data)} semantic page chunks with batch embeddings")

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

    try:
        chunk_data = []
        for metadata, embedding in zip(chunk_metadata, embeddings, strict=False):
            embedding_array = np.array(embedding)
            blob = embedding_array.tobytes()

            chunk_data.append((
                metadata["global_start"],
                metadata["global_end"],
                document_id,
                blob,
                metadata["page_number"]
            ))

        add_chunks_with_page_numbers(chunk_data)

        print(f"Fast semantic PDF ingestion completed: {len(chunk_data)} chunks processed")
        return len(chunk_data)

    except Exception as e:
        print(f"[ERROR] Fast semantic PDF ingestion failed: {e}")
        raise RuntimeError(f"Fast semantic PDF ingestion failed: {str(e)}")

@ray.remote
def chunk_document_optimized(text, maxChunkSize, document_id):
    """
    Chunk documents into smaller pieces with RecursiveCharacterTextSplitter and use optimized batch embedding creation.
    """
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
        for metadata, embedding in zip(chunk_metadata, embeddings, strict=False):
            embedding_array = np.array(embedding)
            blob = embedding_array.tobytes()

            chunk_data.append((
                metadata["start_index"],
                metadata["end_index"],
                document_id,
                blob
            ))

        add_chunks(chunk_data)

        print(f"Successfully processed {len(chunk_data)} semantic chunks with batch embeddings")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[FATAL ERROR] Exception during optimized semantic chunking: {e}")
        raise RuntimeError("Optimized semantic chunking failed due to internal error")


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
    rows = get_chat_chunks(user_email, chat_id)

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
    return add_sources_to_message(message_id, sources)

def add_wf_sources_to_db(prompt_id, sources):
    return add_sources_to_prompt(prompt_id, sources)


def add_message_to_db(text, chat_id, isUser, reasoning=None):
    return add_message(text, chat_id, isUser, reasoning)

def add_prompt_to_db(prompt_text):
    return add_prompt(prompt_text)


def add_answer_to_db(answer, citation_id):
    return add_prompt_answer(answer, citation_id)

def retrieve_docs_from_db(chat_id, user_email):
    return retrieve_docs(chat_id, user_email)

def delete_doc_from_db(doc_id, user_email):
    return delete_doc(doc_id, user_email)

def add_model_key_to_db(model_key, chat_id, user_email):
    return add_model_key(model_key, chat_id, user_email)


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
    return ensure_demo_user(user_email)

#For the SDK
def ensure_SDK_user_exists(user_email):
    return ensure_sdk_user(user_email)

def get_chat_info(chat_id):
    return fetch_chat_info(chat_id)

def get_message_info(answer_id, user_email):
    return fetch_message_info(answer_id, user_email)

def get_text_from_url(web_url):
    response = requests.get(web_url)
    result = p.from_buffer(response.content)
    text = result["content"].strip()
    text = text.replace("\n", "").replace("\t", "")
    #text = "".join(text)
    return text
