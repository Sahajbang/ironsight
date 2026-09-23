import os
import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCE_DB = os.path.join(BACKEND_DIR, "app.db")


@pytest.fixture(scope="session")
def client():
    """App wired to a throwaway copy of the seeded DB, so tests can write freely."""
    if not os.path.exists(SOURCE_DB):
        raise RuntimeError("app.db missing — run `python seed.py` before the tests.")

    from app.db import get_db
    from app.main import app

    tmp_dir = tempfile.mkdtemp(prefix="ironsight-test-")
    tmp_db = os.path.join(tmp_dir, "test.db")
    shutil.copy(SOURCE_DB, tmp_db)

    engine = create_engine(f"sqlite:///{tmp_db}", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def db_session():
    from app.db import SessionLocal

    session = SessionLocal()
    yield session
    session.close()
