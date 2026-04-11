"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
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
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS StripeInfo (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            user_id INTEGER NOT NULL,
            stripe_customer_id VARCHAR(255),
            last_webhook_received TIMESTAMP,
            anchor_date TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS Subscriptions (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            stripe_info_id INTEGER NOT NULL,
            subscription_id VARCHAR(255) NOT NULL,
            start_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            end_date TIMESTAMP,
            paid_user INTEGER NOT NULL,
            is_free_trial INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (stripe_info_id) REFERENCES StripeInfo(id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS freeTrialAllowlist (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            email VARCHAR(255),
            token VARCHAR(255),
            max_non_email_count INTEGER NOT NULL DEFAULT 0,
            token_expiration TIMESTAMP
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS freeTrialsAccessed (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            free_trial_allow_list_id INTEGER,
            user_id INTEGER,
            FOREIGN KEY (free_trial_allow_list_id) REFERENCES freeTrialAllowlist(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER NOT NULL,
            model_type TINYINT NOT NULL DEFAULT 0,
            chat_name TEXT,
            associated_task INTEGER NOT NULL,
            custom_model_key TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS chat_shares (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            chat_id INTEGER NOT NULL,
            share_uuid VARCHAR(255) UNIQUE NOT NULL,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats(id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS chat_share_messages (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            chat_share_id INTEGER NOT NULL,
            role ENUM('user', 'chatbot') NOT NULL,
            message_text TEXT NOT NULL,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_share_id) REFERENCES chat_shares(id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS chat_share_documents (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            chat_share_id INTEGER NOT NULL,
            document_name VARCHAR(255) NOT NULL,
            document_text LONGTEXT,
            storage_key TEXT NOT NULL,
            media_type ENUM('text', 'image', 'video', 'audio') NOT NULL DEFAULT 'text',
            mime_type VARCHAR(255),
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_share_id) REFERENCES chat_shares(id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS chat_share_chunks (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            chat_share_document_id INTEGER NOT NULL,
            start_index INTEGER,
            end_index INTEGER,
            embedding_vector BLOB,
            page_number INTEGER,
            FOREIGN KEY (chat_share_document_id) REFERENCES chat_share_documents(id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            message_text TEXT NOT NULL,
            chat_id INTEGER NOT NULL,
            sent_from_user INTEGER NOT NULL,
            reasoning TEXT DEFAULT NULL,
            relevant_chunks TEXT,
            FOREIGN KEY (chat_id) REFERENCES chats(id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS message_attachments (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            message_id INTEGER NOT NULL,
            media_type ENUM('image', 'audio', 'video') NOT NULL,
            mime_type VARCHAR(255) NOT NULL,
            storage_key TEXT NOT NULL,
            original_filename VARCHAR(255),
            FOREIGN KEY (message_id) REFERENCES messages(id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            chat_id INTEGER,
            storage_key TEXT NOT NULL,
            document_name VARCHAR(255) NOT NULL,
            document_text LONGTEXT,
            media_type ENUM('text', 'image', 'video', 'audio') NOT NULL DEFAULT 'text',
            mime_type VARCHAR(255),
            FOREIGN KEY (chat_id) REFERENCES chats(id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            start_index INTEGER,
            end_index INTEGER,
            document_id INTEGER NOT NULL,
            embedding_vector BLOB,
            page_number INTEGER,
            FOREIGN KEY (document_id) REFERENCES documents(id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            prompt_text TEXT NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS prompt_answers (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            prompt_id INTEGER NOT NULL,
            citation_id INTEGER NOT NULL,
            answer_text TEXT,
            FOREIGN KEY (prompt_id) REFERENCES prompts(id),
            FOREIGN KEY (citation_id) REFERENCES chunks(id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS apiKeys (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER NOT NULL,
            api_key VARCHAR(255),
            key_name VARCHAR(255),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(255),
            path VARCHAR(255)
        )
    """)

    op.execute("INSERT INTO companies (name, path) VALUES ('Anote Chatbot', '/companies/anote')")

    op.execute("""
        CREATE TABLE IF NOT EXISTS user_company_chatbots (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            user_id INTEGER NOT NULL,
            name VARCHAR(255) NOT NULL,
            path VARCHAR(255) NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Indexes
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_message_attachments_message_id ON message_attachments(message_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_sent_from_user ON messages(sent_from_user)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON apiKeys(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_chat_id ON documents(chat_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_prompt_answers_prompt_id ON prompt_answers(prompt_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_prompt_answers_citation_id ON prompt_answers(citation_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_chatbot_unique ON user_company_chatbots(user_id, path)")


def downgrade() -> None:
    # Drop indexes first (some are dropped automatically with tables, but be explicit)
    op.execute("DROP INDEX IF EXISTS idx_user_chatbot_unique ON user_company_chatbots")
    op.execute("DROP INDEX IF EXISTS idx_prompt_answers_citation_id ON prompt_answers")
    op.execute("DROP INDEX IF EXISTS idx_prompt_answers_prompt_id ON prompt_answers")
    op.execute("DROP INDEX IF EXISTS idx_chunks_document_id ON chunks")
    op.execute("DROP INDEX IF EXISTS idx_documents_chat_id ON documents")
    op.execute("DROP INDEX IF EXISTS idx_api_keys_user_id ON apiKeys")
    op.execute("DROP INDEX IF EXISTS idx_messages_sent_from_user ON messages")
    op.execute("DROP INDEX IF EXISTS idx_messages_chat_id ON messages")
    op.execute("DROP INDEX IF EXISTS idx_chats_user_id ON chats")
    op.execute("DROP INDEX IF EXISTS idx_message_attachments_message_id ON message_attachments")

    # Drop tables in reverse dependency order
    op.execute("DROP TABLE IF EXISTS user_company_chatbots")
    op.execute("DROP TABLE IF EXISTS companies")
    op.execute("DROP TABLE IF EXISTS apiKeys")
    op.execute("DROP TABLE IF EXISTS prompt_answers")
    op.execute("DROP TABLE IF EXISTS prompts")
    op.execute("DROP TABLE IF EXISTS chunks")
    op.execute("DROP TABLE IF EXISTS documents")
    op.execute("DROP TABLE IF EXISTS message_attachments")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS chat_share_chunks")
    op.execute("DROP TABLE IF EXISTS chat_share_documents")
    op.execute("DROP TABLE IF EXISTS chat_share_messages")
    op.execute("DROP TABLE IF EXISTS chat_shares")
    op.execute("DROP TABLE IF EXISTS chats")
    op.execute("DROP TABLE IF EXISTS freeTrialsAccessed")
    op.execute("DROP TABLE IF EXISTS freeTrialAllowlist")
    op.execute("DROP TABLE IF EXISTS Subscriptions")
    op.execute("DROP TABLE IF EXISTS StripeInfo")
    op.execute("DROP TABLE IF EXISTS users")
