# src/db.py
from __future__ import annotations

from contextlib import contextmanager

import streamlit as st
from sqlmodel import SQLModel, Session, create_engine


@st.cache_resource
def get_engine():
    db_url = st.secrets.get("DATABASE_URL", "").strip() if hasattr(st, "secrets") else ""
    if db_url:
        return create_engine(db_url, echo=False, pool_pre_ping=True)

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
    Streamlit-friendly DB session.
    Key fix: expire_on_commit=False so objects don't "detach" after commits.
    """
    engine = get_engine()
    session = Session(engine, expire_on_commit=False)
    try:
        yield session

        # Only commit if something changed (prevents unnecessary commits on SELECTs)
        if session.new or session.dirty or session.deleted:
            session.commit()

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
