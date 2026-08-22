import os
import tempfile

# NOTE: sqlite ":memory:" creates a separate DB per connection, which
# breaks FastAPI's TestClient (each request may use a different pooled
# connection). A temp file DB behaves like real sqlite/postgres usage
# and is cleaned up automatically when the process exits.
_TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "risklens_test.db")
if os.path.exists(_TEST_DB_PATH):
    os.remove(_TEST_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ["FORCE_MOCK_LLM"] = "true"

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.db import Base


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
