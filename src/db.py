# src/db.py
from __future__ import annotations

from contextlib import contextmanager

import streamlit as st
from sqlmodel import SQLModel, Session, create_engine


@st.cache_resource
def get_engine():
    # Optional Postgres/Supabase later:
    db_url = st.secrets.get("DATABASE_URL", "").strip() if hasattr(st, "secrets") else ""
    if db_url:
        return create_engine(db_url, echo=False, pool_pre_ping=True)

    # Default SQLite (writable on Streamlit Cloud)
    sqlite_path = st.secrets.get("SQLITE_PATH", "/tmp/bluebeam_consolidator.db")
    sqlite_url = f"sqlite:///{sqlite_path}"

    return create_engine(
        sqlite_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )


def init_db():
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    return engine


@contextmanager
def session_scope():
    """
    Safe database session helper:
    - Opens a session
    - Commits on success
    - Rolls back on error
    - Always closes
    """
    engine = get_engine()
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
