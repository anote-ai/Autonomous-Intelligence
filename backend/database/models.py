"""SQLAlchemy declarative ORM models for all Anote database tables.

These models mirror `database/schema.sql` exactly.  The session factory in
`database/session.py` should be used to obtain a database session.

Gradual migration path
----------------------
Raw MySQL queries in `database/db.py` can be migrated to use these models
incrementally.  New code should prefer the ORM; legacy code can continue to
use the raw connection pool until it is refactored.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BLOB,
    BigInteger,
    Column,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Timestamp,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Core user / auth tables
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created = Column(Timestamp, nullable=False, default=datetime.utcnow)
    email = Column(String(255), unique=True, nullable=False)
    google_id = Column(String(255))
    person_name = Column(String(255))
    profile_pic_url = Column(String(255))
    password_hash = Column(String(255))
    salt = Column(String(255))
    session_token = Column(String(255))
    session_token_expiration = Column(Timestamp)
    password_reset_token = Column(String(255))
    password_reset_token_expiration = Column(Timestamp)
    credits = Column(Integer, nullable=False, default=0)
    credits_updated = Column(Timestamp, nullable=False, default=datetime.utcnow)
    chat_gpt_date = Column(Timestamp, nullable=False, default=datetime.utcnow)
    num_chatgpt_requests = Column(Integer, nullable=False, default=0)

    chats = relationship("Chat", back_populates="user")
    api_keys = relationship("ApiKey", back_populates="user")
    stripe_info = relationship("StripeInfo", back_populates="user", uselist=False)

    __table_args__ = (Index("idx_users_email", "email", unique=True),)


class StripeInfo(Base):
    __tablename__ = "StripeInfo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stripe_customer_id = Column(String(255))
    last_webhook_received = Column(Timestamp)
    anchor_date = Column(Timestamp)

    user = relationship("User", back_populates="stripe_info")
    subscriptions = relationship("Subscription", back_populates="stripe_info")


class Subscription(Base):
    __tablename__ = "Subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stripe_info_id = Column(Integer, ForeignKey("StripeInfo.id"), nullable=False)
    subscription_id = Column(String(255), nullable=False)
    start_date = Column(Timestamp, nullable=False, default=datetime.utcnow)
    end_date = Column(Timestamp)
    paid_user = Column(Integer, nullable=False)
    is_free_trial = Column(Integer, nullable=False, default=0)

    stripe_info = relationship("StripeInfo", back_populates="subscriptions")


class FreeTrialAllowlist(Base):
    __tablename__ = "freeTrialAllowlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created = Column(Timestamp, nullable=False, default=datetime.utcnow)
    email = Column(String(255))
    token = Column(String(255))
    max_non_email_count = Column(Integer, nullable=False, default=0)
    token_expiration = Column(Timestamp)

    free_trials = relationship("FreeTrialAccessed", back_populates="allowlist_entry")


class FreeTrialAccessed(Base):
    __tablename__ = "freeTrialsAccessed"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    created = Column(Timestamp, nullable=False, default=datetime.utcnow)
    free_trial_allow_list_id = Column(Integer, ForeignKey("freeTrialAllowlist.id"))
    user_id = Column(Integer, ForeignKey("users.id"))

    allowlist_entry = relationship("FreeTrialAllowlist", back_populates="free_trials")


# ---------------------------------------------------------------------------
# Chat tables
# ---------------------------------------------------------------------------


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created = Column(Timestamp, nullable=False, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    model_type = Column(Integer, nullable=False, default=0)
    chat_name = Column(Text)
    associated_task = Column(Integer, nullable=False)
    custom_model_key = Column(Text)

    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat")
    documents = relationship("Document", back_populates="chat")
    share = relationship("ChatShare", back_populates="chat", uselist=False)

    __table_args__ = (Index("idx_chats_user_id", "user_id"),)


class ChatShare(Base):
    __tablename__ = "chat_shares"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    share_uuid = Column(String(255), unique=True, nullable=False)
    created = Column(Timestamp, nullable=False, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="share")
    messages = relationship("ChatShareMessage", back_populates="chat_share")
    documents = relationship("ChatShareDocument", back_populates="chat_share")


class ChatShareMessage(Base):
    __tablename__ = "chat_share_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_share_id = Column(Integer, ForeignKey("chat_shares.id"), nullable=False)
    role = Column(Enum("user", "chatbot"), nullable=False)
    message_text = Column(Text, nullable=False)
    created = Column(Timestamp, nullable=False, default=datetime.utcnow)

    chat_share = relationship("ChatShare", back_populates="messages")


class ChatShareDocument(Base):
    __tablename__ = "chat_share_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_share_id = Column(Integer, ForeignKey("chat_shares.id"), nullable=False)
    document_name = Column(String(255), nullable=False)
    document_text = Column(Text)
    storage_key = Column(Text, nullable=False)
    media_type = Column(Enum("text", "image", "video", "audio"), nullable=False, default="text")
    mime_type = Column(String(255))
    created = Column(Timestamp, nullable=False, default=datetime.utcnow)

    chat_share = relationship("ChatShare", back_populates="documents")
    chunks = relationship("ChatShareChunk", back_populates="document")


class ChatShareChunk(Base):
    __tablename__ = "chat_share_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_share_document_id = Column(Integer, ForeignKey("chat_share_documents.id"), nullable=False)
    start_index = Column(Integer)
    end_index = Column(Integer)
    embedding_vector = Column(BLOB)
    page_number = Column(Integer)

    document = relationship("ChatShareDocument", back_populates="chunks")


# ---------------------------------------------------------------------------
# Message tables
# ---------------------------------------------------------------------------


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created = Column(Timestamp, nullable=False, default=datetime.utcnow)
    message_text = Column(Text, nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    sent_from_user = Column(Integer, nullable=False)
    reasoning = Column(Text)
    relevant_chunks = Column(Text)

    chat = relationship("Chat", back_populates="messages")
    attachments = relationship("MessageAttachment", back_populates="message")

    __table_args__ = (
        Index("idx_messages_chat_id", "chat_id"),
        Index("idx_messages_sent_from_user", "sent_from_user"),
    )


class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created = Column(Timestamp, nullable=False, default=datetime.utcnow)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    media_type = Column(Enum("image", "audio", "video"), nullable=False)
    mime_type = Column(String(255), nullable=False)
    storage_key = Column(Text, nullable=False)
    original_filename = Column(String(255))

    message = relationship("Message", back_populates="attachments")

    __table_args__ = (Index("idx_message_attachments_message_id", "message_id"),)


# ---------------------------------------------------------------------------
# Document / chunk tables
# ---------------------------------------------------------------------------


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created = Column(Timestamp, nullable=False, default=datetime.utcnow)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    storage_key = Column(Text, nullable=False)
    document_name = Column(String(255), nullable=False)
    document_text = Column(Text)
    media_type = Column(Enum("text", "image", "video", "audio"), nullable=False, default="text")
    mime_type = Column(String(255))

    chat = relationship("Chat", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document")

    __table_args__ = (Index("idx_documents_chat_id", "chat_id"),)


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_index = Column(Integer)
    end_index = Column(Integer)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    embedding_vector = Column(BLOB)
    page_number = Column(Integer)

    document = relationship("Document", back_populates="chunks")

    __table_args__ = (Index("idx_chunks_document_id", "document_id"),)


# ---------------------------------------------------------------------------
# Prompt / answer tables
# ---------------------------------------------------------------------------


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_text = Column(Text, nullable=False)

    answers = relationship("PromptAnswer", back_populates="prompt")


class PromptAnswer(Base):
    __tablename__ = "prompt_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=False)
    citation_id = Column(Integer, ForeignKey("chunks.id"), nullable=False)
    answer_text = Column(Text)

    prompt = relationship("Prompt", back_populates="answers")

    __table_args__ = (
        Index("idx_prompt_answers_prompt_id", "prompt_id"),
        Index("idx_prompt_answers_citation_id", "citation_id"),
    )


# ---------------------------------------------------------------------------
# API key table
# ---------------------------------------------------------------------------


class ApiKey(Base):
    __tablename__ = "apiKeys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created = Column(Timestamp, nullable=False, default=datetime.utcnow)
    last_used = Column(Timestamp, nullable=False, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    api_key = Column(String(255))
    key_name = Column(String(255))

    user = relationship("User", back_populates="api_keys")

    __table_args__ = (Index("idx_api_keys_user_id", "user_id"),)


# ---------------------------------------------------------------------------
# Company / chatbot tables
# ---------------------------------------------------------------------------


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255))
    path = Column(String(255))


class UserCompanyChatbot(Base):
    __tablename__ = "user_company_chatbots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    path = Column(String(255), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "path", name="idx_user_chatbot_unique"),
    )
