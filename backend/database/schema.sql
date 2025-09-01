DROP TABLE IF EXISTS Subscriptions;
DROP TABLE IF EXISTS StripeInfo;
DROP TABLE IF EXISTS freeTrialsAccessed;
DROP TABLE IF EXISTS prompt_answers;
DROP TABLE IF EXISTS prompts;
DROP TABLE IF EXISTS chunks;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS chat_share_chunks;
DROP TABLE IF EXISTS chat_share_documents;
DROP TABLE IF EXISTS chat_share_messages;
DROP TABLE IF EXISTS chat_shares;
DROP TABLE IF EXISTS chats;
DROP TABLE IF EXISTS apiKeys;
DROP TABLE IF EXISTS user_company_chatbots;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS freeTrialAllowlist;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    email VARCHAR(255) UNIQUE NOT NULL,
    google_id VARCHAR(255),
    person_name VARCHAR(255),
    profile_pic_url VARCHAR(255),
    password_hash VARCHAR(255),
    salt VARCHAR(255),
    session_token VARCHAR(255),
    session_token_expiration TIMESTAMP,
    password_reset_token VARCHAR(255),
    password_reset_token_expiration TIMESTAMP,
    credits INTEGER NOT NULL DEFAULT 0,
    credits_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    chat_gpt_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    num_chatgpt_requests INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE StripeInfo (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id INTEGER NOT NULL,
    stripe_customer_id VARCHAR(255),
    last_webhook_received TIMESTAMP,
    anchor_date TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE Subscriptions (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    stripe_info_id INTEGER NOT NULL,
    subscription_id VARCHAR(255) NOT NULL,
    start_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_date TIMESTAMP, -- NULL if the subscription is active.
    paid_user INTEGER NOT NULL,
    is_free_trial INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (stripe_info_id) REFERENCES StripeInfo(id)
);

CREATE TABLE freeTrialAllowlist (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    email VARCHAR(255),
    token VARCHAR(255),
    max_non_email_count INTEGER NOT NULL DEFAULT 0,
    token_expiration TIMESTAMP
);

CREATE TABLE freeTrialsAccessed (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    free_trial_allow_list_id INTEGER,
    user_id INTEGER,
    FOREIGN KEY (free_trial_allow_list_id) REFERENCES freeTrialAllowlist(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE chats (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL,
    model_type TINYINT NOT NULL DEFAULT 0,
    chat_name TEXT,
    associated_task INTEGER NOT NULL,
    custom_model_key TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE chat_shares (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    chat_id INTEGER NOT NULL,
    share_uuid VARCHAR(255) UNIQUE NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chat_id) REFERENCES chats(id)
);

CREATE TABLE chat_share_messages (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    chat_share_id INTEGER NOT NULL,
    role ENUM('user', 'chatbot') NOT NULL,
    message_text TEXT NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chat_share_id) REFERENCES chat_shares(id)
);

CREATE TABLE chat_share_documents (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    chat_share_id INTEGER NOT NULL,
    document_name VARCHAR(255) NOT NULL,
    document_text LONGTEXT NOT NULL,
    storage_key TEXT NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chat_share_id) REFERENCES chat_shares(id)
);

CREATE TABLE chat_share_chunks (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    chat_share_document_id INTEGER NOT NULL,
    start_index INTEGER,
    end_index INTEGER,
    embedding_vector BLOB,
    page_number INTEGER,
    FOREIGN KEY (chat_share_document_id) REFERENCES chat_share_documents(id)
);


CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    message_text TEXT NOT NULL,
    chat_id INTEGER NOT NULL,
    sent_from_user INTEGER NOT NULL,
    reasoning TEXT DEFAULT(NULL),
    relevant_chunks TEXT,
    FOREIGN KEY (chat_id) REFERENCES chats(id)
);

CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    chat_id INTEGER,
    storage_key TEXT NOT NULL,
    document_name VARCHAR(255) NOT NULL,
    document_text LONGTEXT NOT NULL,
    FOREIGN KEY (chat_id) REFERENCES chats(id)
);

CREATE TABLE chunks (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    start_index INTEGER,
    end_index INTEGER,
    document_id INTEGER NOT NULL,
    embedding_vector BLOB,
    page_number INTEGER,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

CREATE TABLE prompts (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    prompt_text TEXT NOT NULL
);

CREATE TABLE prompt_answers (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    prompt_id INTEGER NOT NULL,
    citation_id INTEGER NOT NULL,
    answer_text TEXT,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id),
    FOREIGN KEY (citation_id) REFERENCES chunks(id)
);


CREATE TABLE apiKeys (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL,
    api_key VARCHAR(255),
    key_name VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS companies (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(255),
  path VARCHAR(255)
  -- other columns
);
INSERT INTO companies (name, path) VALUES ('Anote Chatbot', '/companies/anote');


CREATE TABLE user_company_chatbots (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    path VARCHAR(255) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);



CREATE UNIQUE INDEX idx_users_email ON users(email);
CREATE INDEX idx_chats_user_id ON chats(user_id);
CREATE INDEX idx_messages_chat_id ON messages(chat_id);
CREATE INDEX idx_messages_sent_from_user ON messages(sent_from_user);
CREATE INDEX idx_api_keys_user_id ON apiKeys(user_id);
CREATE INDEX idx_documents_chat_id ON documents(chat_id);
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_prompt_answers_prompt_id ON prompt_answers(prompt_id);
CREATE INDEX idx_prompt_answers_citation_id ON prompt_answers(citation_id);
CREATE UNIQUE INDEX idx_user_chatbot_unique ON user_company_chatbots(user_id, path);
