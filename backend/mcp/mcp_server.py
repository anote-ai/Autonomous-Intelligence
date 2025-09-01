#!/usr/bin/env python3

import os
import sys
import json
import ray
from typing import Dict, List, Any

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)

from fastmcp import FastMCP
from database.db import get_db_connection
from api_endpoints.financeGPT.chatbot_endpoints import (
    get_relevant_chunks, add_document_to_db, chunk_document,
    retrieve_docs_from_db, delete_doc_from_db, add_message_to_db,
    add_sources_to_db, retrieve_message_from_db, get_relevant_chunks_wf,
    add_ticker_to_workflow_db, add_prompt_to_workflow_db,
    get_text_from_single_file, get_text_from_url
)

# Initialize FastMCP server
mcp = FastMCP("Document Agent Server")

@mcp.tool()
def retrieve_relevant_chunks(query: str, chat_id: int, user_email: str, k: int = 2) -> str:
    """Retrieve relevant document chunks based on a given user query"""

    try:
        sources = get_relevant_chunks(k, query, chat_id, user_email)

        if not sources or sources == ["No text found"]:
            return "No relevant documents found."

        result = []
        for i, (chunk_text, document_name) in enumerate(sources):
            result.append(f"Source {i+1} ({document_name}):\n{chunk_text}")

        return "\n\n---\n\n".join(result)
    except Exception as e:
        return f"Error retrieving documents: {str(e)}"

@mcp.tool()
def ingest_document(text: str, document_name: str, chat_id: int, chunk_size: int = 1000) -> str:
    """Ingest a document and create embeddings"""
    try:
        doc_id, exists = add_document_to_db(text, document_name, chat_id)

        if not exists:
            # Process document asynchronously
            chunk_document.remote(text, chunk_size, doc_id)

        return f"Document '{document_name}' ingested successfully. Document ID: {doc_id}"
    except Exception as e:
        return f"Error ingesting document: {str(e)}"

@mcp.tool()
def list_documents(chat_id: int, user_email: str) -> str:
    """List all documents in a chat"""
    try:
        docs = retrieve_docs_from_db(chat_id, user_email)

        if not docs:
            return "No documents found in this chat."

        doc_list = []
        for doc in docs:
            doc_list.append(f"ID: {doc['id']} - {doc['document_name']}")

        return "Documents:\n" + "\n".join(doc_list)
    except Exception as e:
        return f"Error listing documents: {str(e)}"

@mcp.tool()
def delete_document(doc_id: int, user_email: str) -> str:
    """Delete a document and its chunks"""
    try:
        result = delete_doc_from_db(doc_id, user_email)
        return f"Document deletion result: {result}"
    except Exception as e:
        return f"Error deleting document: {str(e)}"

@mcp.tool()
def add_message(message_text: str, chat_id: int, is_user: int) -> str:
    """Add a message to the chat history"""
    try:
        message_id = add_message_to_db(message_text, chat_id, is_user)
        return f"Message added with ID: {message_id}"
    except Exception as e:
        return f"Error adding message: {str(e)}"

@mcp.tool()
def get_chat_history(chat_id: int, user_email: str, chat_type: int = 0) -> str:
    """Retrieve chat message history"""
    try:
        messages = retrieve_message_from_db(user_email, chat_id, chat_type)

        if not messages:
            return "No chat history found."

        history = []
        for msg in messages[-10:]:  # Last 10 messages
            role = "User" if msg['sent_from_user'] == 1 else "Assistant"
            history.append(f"{role}: {msg['message_text']}")

        return "\n\n".join(history)
    except Exception as e:
        return f"Error retrieving chat history: {str(e)}"

@mcp.tool()
def add_sources_to_message(message_id: int, sources: List[List[str]]) -> str:
    """Add source citations to a message"""
    try:
        # Convert sources to the expected format
        formatted_sources = [(source[0], source[1]) for source in sources]
        add_sources_to_db(message_id, formatted_sources)
        return "Sources added to message successfully."
    except Exception as e:
        return f"Error adding sources: {str(e)}"

@mcp.tool()
def retrieve_workflow_chunks(query: str, workflow_id: int, user_email: str, k: int = 2) -> str:
    """Retrieve relevant chunks for workflow queries"""
    try:
        sources = get_relevant_chunks_wf(k, query, workflow_id, user_email)

        if not sources or sources == ["No text found"]:
            return "No relevant workflow documents found."

        result = []
        for i, (chunk_text, document_name) in enumerate(sources):
            result.append(f"Source {i+1} ({document_name}):\n{chunk_text}")

        return "\n\n---\n\n".join(result)
    except Exception as e:
        return f"Error retrieving workflow chunks: {str(e)}"

@mcp.tool()
def extract_text_from_url(url: str) -> str:
    """Extract text content from a URL"""
    try:
        text = get_text_from_url(url)
        return f"Extracted text from {url}:\n\n{text[:1000]}..."
    except Exception as e:
        return f"Error extracting text from URL: {str(e)}"

@mcp.tool()
def execute_database_query(query: str, params: List[str] = None) -> str:
    """Execute a database query"""
    if params is None:
        params = []

    try:
        conn, cursor = get_db_connection()
        cursor.execute(query, params)

        if query.strip().upper().startswith("SELECT"):
            results = cursor.fetchall()
            conn.close()
            return json.dumps(results, default=str)
        else:
            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()
            return f"Query executed. Affected rows: {affected_rows}"
    except Exception as e:
        return f"Database query error: {str(e)}"

if __name__ == "__main__":
    # Initialize Ray if needed
    if not ray.is_initialized():
        try:
            ray.init(ignore_reinit_error=True)
            print("Ray initialized successfully")
        except Exception as e:
            print(f"Ray initialization failed: {e}")

    # Run the FastMCP server
    mcp.run()