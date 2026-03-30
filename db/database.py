import os
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


def _get_database_url():
    """
    Resolve database URL in priority order:
    1. Streamlit secrets (for Streamlit Cloud deployment)
    2. Environment variable (for other deployments)
    3. Local SQLite (for development)
    """
    try:
        url = st.secrets["DATABASE_URL"]
    except (KeyError, FileNotFoundError):
        url = os.environ.get("DATABASE_URL")

    if url:
        # Supabase gives "postgres://" but SQLAlchemy requires "postgresql://"
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    # Local SQLite fallback
    db_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(db_dir, "audit_dashboard.db")
    return f"sqlite:///{db_path}"


DATABASE_URL = _get_database_url()
_is_postgres = DATABASE_URL.startswith("postgresql")

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_session() -> Session:
    return SessionLocal()


def init_db():
    """Create all tables if they don't exist."""
    from db.models import Base
    Base.metadata.create_all(engine)
