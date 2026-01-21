# src/db.py
from __future__ import annotations

import os
import streamlit as st
from sqlmodel import SQLModel, create_engine


@st.cache_resource
def get_engine():
    # If you later use Postgres/Supabase, set DATABASE_URL in Streamlit Secrets.
    db_url = st.secrets.get("DATABASE_URL", "").strip() if hasattr(st, "secrets") else ""

    if db_url:
        # Example: postgres connection string
        return create_engine(db_url, echo=False, pool_pre_ping=True)

    # Default: SQLite in a writable path on Streamlit Cloud
    # /tmp is writable; the repo folder can be read-only.
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
