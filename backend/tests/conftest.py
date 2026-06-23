"""Shared test fixtures.

DB-touching tests run against an in-memory SQLite database so they need no
Postgres and no network. We point DATABASE_URL at SQLite *before* any app module
imports, since app.database builds its engine at import time. The pure triage
contract tests (test_triage.py) don't import the DB and are unaffected.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("TRIAGE_ENABLED", "false")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
import app.models  # noqa: F401  (register models on Base.metadata)


@pytest.fixture
def db():
    # A single shared in-memory connection for the test's lifetime.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
