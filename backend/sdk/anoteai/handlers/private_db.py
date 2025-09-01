import os
import sqlite3
import numpy as np
import openai
import requests
import PyPDF2
import ray
import logging

sec_api_key=os.environ.get('sec_api_key')

USER_ID = 1
## Private methods
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db_connection():
    db_path = os.environ.get('DB_PATH', './database.db') #somehow has to get the path to the .db file inside the private chatbot app

    conn = sqlite3.connect(db_path)
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    return conn, cursor

def create_db_file():
    db_exists = os.path.exists('database.db')

    connection = sqlite3.connect('database.db')
    cur = connection.cursor()

    if not db_exists:
        with open('schema.sql') as f:
            connection.executescript(f.read())

        insert_sql = """
        INSERT INTO users (
            session_token,
            session_token_expiration,
            password_reset_token,
            password_reset_token_expiration,
            credits,
            credits_updated,
            chat_gpt_date,
            num_chatgpt_requests
        ) VALUES (
            'sessionToken123',
            '2023-01-01 00:00:00',
            'passwordResetToken123',
            '2023-01-01 00:00:00',
            10,
            '2023-01-01 00:00:00',
            '2023-01-01 00:00:00',
            5
        );
        """
        cur.execute(insert_sql)

    cur.execute('SELECT id FROM users')
    users = cur.fetchone()

    connection.commit()
    connection.close()

    #return users
    return users[0]

def ensure_SDK_user_exists(user_email):
    conn, cursor = get_db_connection()

    cursor.execute("SELECT id FROM users WHERE email = ?", (user_email,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        insert_query = """
        INSERT INTO users (email, person_name, profile_pic_url, credits)
        VALUES (?, 'SDK User', 'url_to_default_image', 0)
        """
        cursor.execute(insert_query, (user_email,))
        conn.commit()
        return cursor.lastrowid

def add_message_to_db(text, chat_id, isUser):
    #If isUser is 0, it is a bot message, 1 is a user message
    conn, cursor = get_db_connection()

    cursor.execute('INSERT INTO messages (message_text, chat_id, sent_from_user) VALUES (?,?,?)', (text, chat_id, isUser))
    message_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return message_id

def get_chat_info(chat_id):
    conn, cursor = get_db_connection()

    cursor.execute("SELECT model_type, associated_task FROM chats WHERE id = ?", (chat_id,))
    result = cursor.fetchone()

    if result:
        model_type = result['model_type']
        associated_task = result['associated_task']
    else:
        model_type, associated_task = None, None
    cursor.close()
    conn.close()

    return model_type, associated_task

def get_relevant_chunks(k, question, chat_id):
    conn, cursor = get_db_connection()

    query = """
    SELECT c.start_index, c.end_index, c.embedding_vector, c.document_id, c.page_number, d.document_name
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    JOIN chats ch ON d.chat_id = ch.id
    JOIN users u ON ch.user_id = u.id
    WHERE u.id = ? AND ch.id = ?
    """

    cursor.execute(query, (USER_ID, chat_id))
    rows = cursor.fetchall()

    embeddings = []
    for row in rows:
        embeddingVectorBlob = row["embedding_vector"]
        embeddingVector = np.frombuffer(embeddingVectorBlob)
        embeddings.append(embeddingVector)

    if (len(embeddings) == 0):
        res_list = []
        for i in range(k):
            res_list.append("No text found")
        return res_list

    embeddings = np.array(embeddings)

    embeddingVector = openai.embeddings.create(input=question, model="text-embedding-ada-002").data[0].embedding
    embeddingVector = np.array(embeddingVector)

    res = knn(embeddingVector, embeddings)
    num_results = min(k, len(res))

    #Get the k most relevant chunks
    source_chunks = []
    for i in range(num_results):
        source_id = res[i]['index']

        document_id = rows[source_id]['document_id']
        page_number = rows[source_id]['page_number']
        document_name = rows[source_id]['document_name']


        cursor.execute('SELECT document_text FROM documents WHERE id = ?', (document_id,))
        doc_text = cursor.fetchone()['document_text']

        source_chunk = doc_text[rows[source_id]['start_index']:rows[source_id]['end_index']]
        source_chunks.append((source_chunk, document_name))

    return source_chunks


def knn(x, y):
    x = np.expand_dims(x, axis=0)
    # Calculate cosine similarity
    similarities = np.dot(x, y.T) / (np.linalg.norm(x) * np.linalg.norm(y))
    # Convert similarities to distances
    distances = 1 - similarities.flatten()
    nearest_neighbors = np.argsort(distances)

    results = []
    for i in range(len(nearest_neighbors)):
        item = {
            "index": nearest_neighbors[i],
            "similarity_score": distances[nearest_neighbors[i]]
        }
        results.append(item)

    return results

def add_sources_to_db(message_id, sources):
    combined_sources = ""

    for source in sources:
        chunk_text, document_name = source
        combined_sources += f"Document: {document_name}: {chunk_text}\n\n"

    conn, cursor = get_db_connection()

    cursor.execute('UPDATE messages SET relevant_chunks = ? WHERE id = ?', (combined_sources, message_id))

    conn.commit()

    cursor.close()
    conn.close()


def add_document_to_db(text, document_name, chat_id):
    conn, cursor = get_db_connection()

    cursor.execute("SELECT id, document_text FROM documents WHERE document_name = ? AND chat_id = ?", (document_name, chat_id))
    existing_doc = cursor.fetchone()

    if existing_doc:
        existing_doc_id, existing_doc_text = existing_doc
        conn.close()
        return existing_doc_id, True  # Returning the ID of the existing document


    storage_key = "temp"
    cursor.execute("INSERT INTO documents (chat_id, document_name, document_text, storage_key) VALUES (?, ?, ?, ?)", (chat_id, document_name, text, storage_key))

    doc_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return doc_id, False



@ray.remote
def chunk_document(text, maxChunkSize, document_id):
    conn, cursor = get_db_connection()

    chunks = []
    startIndex = 0

    while startIndex < len(text):
        endIndex = startIndex + min(maxChunkSize, len(text))
        chunkText = text[startIndex:endIndex]
        chunkText = chunkText.replace("\n", "")

        embeddingVector = openai.embeddings.create(input=chunkText, model="text-embedding-ada-002").data[0].embedding
        embeddingVector = np.array(embeddingVector)
        blob = embeddingVector.tobytes()
        chunks.append({
            "text": chunkText,
            "start_index": startIndex,
            "end_index": endIndex,
            "embedding_vector": embeddingVector,
            "embedding_vector_blob": blob,
        })
        startIndex += maxChunkSize

    for chunk in chunks:
        cursor.execute('INSERT INTO chunks (start_index, end_index, document_id, embedding_vector) VALUES (?,?,?,?)', [chunk["start_index"], chunk["end_index"], document_id, chunk["embedding_vector_blob"]])

    conn.commit()
    conn.close()

def reset_uploaded_docs(chat_id):
    conn, cursor = get_db_connection()

    delete_chunks_query = """
    DELETE FROM chunks
    WHERE document_id IN (
        SELECT id FROM documents
        WHERE chat_id = ?
    )
    """
    cursor.execute(delete_chunks_query, (chat_id,))

    delete_documents_query = """
    DELETE FROM documents
    WHERE chat_id = ? AND EXISTS (
        SELECT 1 FROM chats
        WHERE chats.id = documents.chat_id
        AND chats.user_id = ?
    )
    """
    cursor.execute(delete_documents_query, (chat_id, USER_ID))

    conn.commit()

    conn.close()


def get_text_from_single_file(file):
    reader = PyPDF2.PdfReader(file)
    text = ""

    for page_num in range(len(reader.pages)):

        text += reader.pages[page_num].extract_text()

    return text

def get_message_info(answer_id):
    conn, cursor = get_db_connection()

    answer_query = "SELECT chat_id, message_text, relevant_chunks FROM messages WHERE id = ?"

    cursor.execute(answer_query, (answer_id, ))
    answer = cursor.fetchone()

    if not answer:
        print("Either the answer does not exist or it doesn't belong to the specified user.")
        return None, None

    chat_id = answer['chat_id']

    question_query = """
    SELECT m.*
    FROM messages m
    WHERE m.id < ? AND m.chat_id = ? AND m.sent_from_user = 1
    ORDER BY m.id DESC
    LIMIT 1
    """

    cursor.execute(question_query, (answer_id, chat_id))
    question = cursor.fetchone()

    cursor.close()
    return question, answer