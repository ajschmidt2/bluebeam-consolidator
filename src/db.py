from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlmodel import SQLModel, Session, create_engine


def _default_db_url() -> str:
    # Prefer Streamlit secrets / env var; fall back to local SQLite file.
    return os.getenv("DATABASE_URL", "sqlite:///./data/app.db")


def get_engine(db_url: Optional[str] = None):
    url = db_url or _default_db_url()

    # Ensure sqlite path dir exists for file-based sqlite URLs.
    if url.startswith("sqlite") and ":///" in url:
        path = url.split(":///", 1)[1]
        if path and path not in (":memory:", "/:memory:"):
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, echo=False, connect_args=connect_args)


ENGINE = get_engine()


def init_db() -> None:
    SQLModel.metadata.create_all(ENGINE)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    with Session(ENGINE) as session:
        yield session
