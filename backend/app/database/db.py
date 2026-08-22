"""
SQLAlchemy engine/session setup.

Works against PostgreSQL (the default, used by docker-compose) but also
against SQLite (used automatically by the test suite) — both are
supported so `pytest` can run without a live Postgres instance.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config.settings import get_settings

settings = get_settings()

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they do not already exist. Called on backend startup
    so the user never has to run migrations or create the database by hand."""
    from app.models import models  # noqa: F401  (ensures models are registered)
    Base.metadata.create_all(bind=engine)
