import ipaddress
import socket
import threading
from urllib.parse import urlparse

import numpy as np
import PyPDF2
import ray
import requests
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI
from tika import parser as p

from database.db import add_chunks, add_chunks_with_page_numbers, get_chat_chunks

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 768
MAX_CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200

_embedding_model = None
_client = OpenAI()
_model_lock = threading.Lock()
_splitter_lock = threading.RLock()
_text_splitters = {}


class UnsafeUrlError(ValueError):
    pass


def validate_external_url(web_url: str) -> None:
    parsed = urlparse(web_url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeUrlError("Only http and https URLs are allowed")
    if not parsed.hostname or parsed.username or parsed.password:
        raise UnsafeUrlError("Invalid URL")

    try:
        address_info = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as err:
        raise UnsafeUrlError("Could not resolve host") from err

    for _, _, _, _, sockaddr in address_info:
        ip = ipaddress.ip_address(sockaddr[0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise UnsafeUrlError("URL resolves to a non-public address")


def fetch_external_url(web_url: str) -> requests.Response:
    validate_external_url(web_url)
    return requests.get(web_url, timeout=10, allow_redirects=False)


def _get_model():
    global _embedding_model

    if _embedding_model:
        print("Skipping embedding model init")
        return _embedding_model

    with _model_lock:
        if _embedding_model is None:
            print(f"Using OpenAI embedding model: {EMBEDDING_MODEL}")

            def embed_fn(texts):
                if isinstance(texts, str):
                    texts = [texts]

                response = _client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
                return [item.embedding for item in response.data]

            _embedding_model = embed_fn

    return _embedding_model


def _get_text_splitter(chunk_size=None):
    global _text_splitters

    if chunk_size is None:
        chunk_size = MAX_CHUNK_SIZE

    if chunk_size not in _text_splitters:
        try:
            with _splitter_lock:
                if chunk_size not in _text_splitters:
                    print(
                        f"Initializing RecursiveCharacterTextSplitter with chunk_size={chunk_size}..."
                    )
                    _text_splitters[chunk_size] = RecursiveCharacterTextSplitter(
                        chunk_size=chunk_size,
                        chunk_overlap=CHUNK_OVERLAP,
                        separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
                        length_function=len,
                    )
                    print(
                        f"RecursiveCharacterTextSplitter (chunk_size={chunk_size}) initialized successfully!"
                    )
        except Exception as err:
            print(f"[ERROR] Failed to initialize text splitter: {err}")
            raise RuntimeError(f"Text splitter initialization failed: {err}") from err

    return _text_splitters[chunk_size]


def preload_text_splitter():
    try:
        print("Preloading RecursiveCharacterTextSplitter for faster document processing...")
        _get_text_splitter()
        print("RecursiveCharacterTextSplitter preloaded successfully!")
    except Exception as err:
        print(f"[WARNING] Failed to preload text splitter: {err}")


def preload_embedding_model():
    try:
        print("Preloading embedding model for faster PDF processing...")
        _get_model()
        print("Embedding model preloaded successfully!")
    except Exception as err:
        print(f"[WARNING] Failed to preload embedding model: {err}")


def preload_models():
    preload_text_splitter()
    preload_embedding_model()


def get_embedding(question):
    try:
        model = _get_model()
        embedding = model(f"query: {question}")[0]
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                f"Unexpected embedding dimension: {len(embedding)}, expected {EMBEDDING_DIMENSIONS}"
            )
        return embedding
    except Exception as err:
        print(f"[ERROR] Failed to get embedding: {err}")
        raise RuntimeError(f"Embedding generation failed: {err}") from err


def get_embeddings_batch(texts, batch_size=32):
    try:
        model = _get_model()
        embeddings = []

        for index in range(0, len(texts), batch_size):
            batch_texts = texts[index : index + batch_size]
            prefixed_texts = [f"passage: {text}" for text in batch_texts]
            embeddings.extend(model(prefixed_texts))
            print(
                f"Processed batch {index // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size}"
            )

        return embeddings
    except Exception as err:
        print(f"[ERROR] Failed to get batch embeddings: {err}")
        raise RuntimeError(f"Batch embedding generation failed: {err}") from err


def prepare_chunks_for_embedding(text_pages, max_chunk_size):
    chunk_texts = []
    chunk_metadata = []
    global_start_index = 0
    page_number = 1
    text_splitter = _get_text_splitter(max_chunk_size)

    for page_text in text_pages:
        page_chunks = text_splitter.split_text(page_text)
        page_position = 0
        for chunk in page_chunks:
            chunk_start_in_page = page_text.find(chunk, page_position)
            if chunk_start_in_page == -1:
                chunk_start_in_page = page_text.find(chunk)

            chunk_end_in_page = chunk_start_in_page + len(chunk)
            chunk_texts.append(chunk)
            chunk_metadata.append(
                {
                    "global_start": global_start_index + chunk_start_in_page,
                    "global_end": global_start_index + chunk_end_in_page,
                    "page_number": page_number,
                }
            )
            page_position = chunk_start_in_page + 1

        global_start_index += len(page_text)
        page_number += 1

    return chunk_texts, chunk_metadata


@ray.remote
def chunk_document_by_page_optimized(text_pages, max_chunk_size, document_id):
    print("start optimized semantic page chunk doc")
    chunk_texts = []
    chunk_metadata = []
    global_start_index = 0
    page_number = 1

    try:
        text_splitter = _get_text_splitter(max_chunk_size)

        for page_text in text_pages:
            page_chunks = text_splitter.split_text(page_text)
            print(f"Page {page_number}: Created {len(page_chunks)} semantic chunks")
            page_position = 0

            for chunk in page_chunks:
                chunk_start_in_page = page_text.find(chunk, page_position)
                if chunk_start_in_page == -1:
                    chunk_start_in_page = page_text.find(chunk)

                chunk_end_in_page = chunk_start_in_page + len(chunk)
                chunk_texts.append(chunk)
                chunk_metadata.append(
                    {
                        "global_start": global_start_index + chunk_start_in_page,
                        "global_end": global_start_index + chunk_end_in_page,
                        "page_number": page_number,
                    }
                )
                page_position = chunk_start_in_page + 1

            global_start_index += len(page_text)
            page_number += 1

        print(f"Generating embeddings for {len(chunk_texts)} semantic page chunks in batches...")
        embeddings = get_embeddings_batch(chunk_texts, batch_size=32)

        for index, embedding in enumerate(embeddings):
            if len(embedding) != EMBEDDING_DIMENSIONS:
                raise RuntimeError(
                    f"Page chunk {index} embedding dimension mismatch: expected {EMBEDDING_DIMENSIONS}, got {len(embedding)}"
                )

        chunk_data = []
        for metadata, embedding in zip(chunk_metadata, embeddings, strict=False):
            chunk_data.append(
                (
                    metadata["global_start"],
                    metadata["global_end"],
                    document_id,
                    np.array(embedding).tobytes(),
                    metadata["page_number"],
                )
            )

        add_chunks_with_page_numbers(chunk_data)
        print(f"Successfully processed {len(chunk_data)} semantic page chunks with batch embeddings")
    except Exception as err:
        print(f"[FATAL ERROR] Exception during optimized semantic page chunking: {err}")
        raise RuntimeError(
            "Optimized semantic page chunking failed due to internal error"
        ) from err


@ray.remote
def chunk_document_by_page(text_pages, max_chunk_size, document_id):
    return chunk_document_by_page_optimized.remote(text_pages, max_chunk_size, document_id)


@ray.remote
def chunk_document_optimized(text, max_chunk_size, document_id):
    chunk_texts = []
    chunk_metadata = []

    try:
        text_splitter = _get_text_splitter(max_chunk_size)
        chunks = text_splitter.split_text(text)
        print(f"RecursiveCharacterTextSplitter created {len(chunks)} semantic chunks")

        current_position = 0
        for chunk in chunks:
            chunk_start = text.find(chunk, current_position)
            if chunk_start == -1:
                chunk_start = text.find(chunk)

            chunk_texts.append(chunk)
            chunk_metadata.append(
                {
                    "start_index": chunk_start,
                    "end_index": chunk_start + len(chunk),
                }
            )
            current_position = chunk_start + 1

        print(f"Generating embeddings for {len(chunk_texts)} semantic chunks in batches...")
        embeddings = get_embeddings_batch(chunk_texts, batch_size=32)

        for index, embedding in enumerate(embeddings):
            if len(embedding) != EMBEDDING_DIMENSIONS:
                raise RuntimeError(
                    f"Chunk {index} embedding dimension mismatch: expected {EMBEDDING_DIMENSIONS}, got {len(embedding)}"
                )

        chunk_data = []
        for metadata, embedding in zip(chunk_metadata, embeddings, strict=False):
            chunk_data.append(
                (
                    metadata["start_index"],
                    metadata["end_index"],
                    document_id,
                    np.array(embedding).tobytes(),
                )
            )

        add_chunks(chunk_data)
        print(f"Successfully processed {len(chunk_data)} semantic chunks with batch embeddings")
    except Exception as err:
        print(f"[FATAL ERROR] Exception during optimized semantic chunking: {err}")
        raise RuntimeError("Optimized semantic chunking failed due to internal error") from err


@ray.remote
def chunk_document(text, max_chunk_size, document_id):
    return chunk_document_optimized.remote(text, max_chunk_size, document_id)


def fast_pdf_ingestion(text_pages, max_chunk_size, document_id):
    print(f"Starting fast semantic PDF ingestion for document {document_id}")
    chunk_texts, chunk_metadata = prepare_chunks_for_embedding(text_pages, max_chunk_size)
    print(f"Prepared {len(chunk_texts)} semantic chunks for processing")
    print("Generating embeddings in optimized batches...")
    embeddings = get_embeddings_batch(chunk_texts, batch_size=64)

    for index, embedding in enumerate(embeddings):
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                f"Chunk {index} embedding dimension mismatch: expected {EMBEDDING_DIMENSIONS}, got {len(embedding)}"
            )

    try:
        chunk_data = []
        for metadata, embedding in zip(chunk_metadata, embeddings, strict=False):
            chunk_data.append(
                (
                    metadata["global_start"],
                    metadata["global_end"],
                    document_id,
                    np.array(embedding).tobytes(),
                    metadata["page_number"],
                )
            )

        add_chunks_with_page_numbers(chunk_data)
        print(f"Fast semantic PDF ingestion completed: {len(chunk_data)} chunks processed")
        return len(chunk_data)
    except Exception as err:
        print(f"[ERROR] Fast semantic PDF ingestion failed: {err}")
        raise RuntimeError(f"Fast semantic PDF ingestion failed: {err}") from err


def knn(query_vector, document_vectors):
    if query_vector.ndim == 1:
        query_vector = np.expand_dims(query_vector, axis=0)
    if document_vectors.ndim == 1:
        document_vectors = np.expand_dims(document_vectors, axis=0)
    if query_vector.shape[1] != document_vectors.shape[1]:
        raise ValueError(
            f"Dimension mismatch: query has {query_vector.shape[1]} dims, documents have {document_vectors.shape[1]} dims"
        )

    query_norm = np.linalg.norm(query_vector, axis=1, keepdims=True)
    document_norm = np.linalg.norm(document_vectors, axis=1, keepdims=True)
    query_norm = np.where(query_norm == 0, 1e-8, query_norm)
    document_norm = np.where(document_norm == 0, 1e-8, document_norm)

    similarities = np.dot(
        query_vector / query_norm, (document_vectors / document_norm).T
    ).flatten()
    distances = 1 - similarities
    nearest_neighbors = np.argsort(distances)

    return [
        {"index": nearest_neighbors[index], "similarity_score": distances[nearest_neighbors[index]]}
        for index in range(len(nearest_neighbors))
    ]


def get_relevant_chunks(k, question, chat_id, user_email):
    rows = get_chat_chunks(user_email, chat_id)
    chunk_embeddings = []
    chunk_metadata = []

    for row in rows:
        embedding = np.frombuffer(row["embedding_vector"])
        if len(embedding) != EMBEDDING_DIMENSIONS:
            print(f"[WARNING] Skipping chunk with bad dimensions: {len(embedding)}")
            continue

        chunk_embeddings.append(embedding)
        chunk_metadata.append(
            {
                "start": row["start_index"],
                "end": row["end_index"],
                "document_name": row["document_name"],
                "document_text": row["document_text"],
            }
        )

    if not chunk_embeddings:
        return []

    try:
        query_embedding = np.array(get_embedding(question))
        if len(query_embedding) != EMBEDDING_DIMENSIONS:
            raise ValueError(f"Query embedding has wrong dimensions: {len(query_embedding)}")
    except Exception as err:
        print(f"[ERROR] Failed to generate query embedding: {err}")
        return []

    results = knn(query_embedding, np.array(chunk_embeddings))
    source_chunks = []
    for index in range(min(k, len(results))):
        metadata = chunk_metadata[results[index]["index"]]
        source_chunks.append(
            (
                metadata["document_text"][metadata["start"] : metadata["end"]],
                metadata["document_name"],
            )
        )
    return source_chunks


def get_text_from_single_file(file):
    reader = PyPDF2.PdfReader(file)
    return "".join(page.extract_text() for page in reader.pages)


def get_text_pages_from_single_file(file):
    reader = PyPDF2.PdfReader(file)
    return [page.extract_text() for page in reader.pages]


def get_text_from_url(web_url):
    response = fetch_external_url(web_url)
    result = p.from_buffer(response.content)
    return result.get("content", "").strip().replace("\n", "").replace("\t", "")
