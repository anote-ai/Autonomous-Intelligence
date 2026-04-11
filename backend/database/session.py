"""SQLAlchemy session factory for the Anote database.

Usage
-----
Use :func:`get_db` as a context manager or dependency::

    from database.session import get_db

    with next(get_db()) as db:
        users = db.query(User).all()

Or use :attr:`SessionLocal` directly for scripts::

    from database.session import SessionLocal
    db = SessionLocal()
    try:
        ...
    finally:
        db.close()
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

load_dotenv()


def get_db_url() -> str:
    """Build a SQLAlchemy-compatible MySQL URL from environment variables."""
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "password")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "anote")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"


def get_engine():
    """Create (or reuse) the SQLAlchemy engine."""
    return create_engine(
        get_db_url(),
        pool_pre_ping=True,   # verify connections before use
        pool_recycle=3600,    # recycle connections every hour
        echo=os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true",
    )


# Module-level session factory — created lazily on first use.
SessionLocal: sessionmaker[Session] = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=get_engine(),
)


def get_db():
    """Yield a database session and ensure it is closed afterwards.

    Intended for use with FastAPI-style dependency injection or plain
    ``next(get_db())`` in synchronous contexts.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
