import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "audit_dashboard.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def get_session() -> Session:
    return SessionLocal()


def init_db():
    """Create all tables if they don't exist."""
    from db.models import Base
    Base.metadata.create_all(engine)
