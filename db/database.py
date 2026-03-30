import os
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


def _get_database_url():
    """
    Get database URL from Streamlit secrets (Supabase) or fall back to local SQLite.
    For Streamlit Cloud: set DATABASE_URL in .streamlit/secrets.toml or app secrets.
    For local development: uses SQLite by default.
    """
    # 1. Check Streamlit secrets (for Streamlit Cloud deployment)
    try:
        return st.secrets["DATABASE_URL"]
    except (KeyError, FileNotFoundError):
        pass

    # 2. Check environment variable
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return db_url

    # 3. Fall back to local SQLite
    db_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(db_dir, "audit_dashboard.db")
    return f"sqlite:///{db_path}"


DATABASE_URL = _get_database_url()

# PostgreSQL from Supabase uses "postgresql://" prefix
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def get_session() -> Session:
    return SessionLocal()


def init_db():
    """Create all tables if they don't exist."""
    from db.models import Base
    Base.metadata.create_all(engine)
