# src/models.py
from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlmodel import SQLModel, Field


class AppSetting(SQLModel, table=True):
    __tablename__ = "app_setting"
    __table_args__ = {"extend_existing": True}

    key: str = Field(primary_key=True)
    value: str = Field(default="")
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Project(SQLModel, table=True):
    __tablename__ = "project"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)

    name: str = Field(index=True)
    client: Optional[str] = Field(default=None)
    location: Optional[str] = Field(default=None)

    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Milestone(SQLModel, table=True):
    __tablename__ = "milestone"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)

    project_id: int = Field(index=True)
    name: str = Field(index=True)

    target_date: Optional[date] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ImportBatch(SQLModel, table=True):
    __tablename__ = "import_batch"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)

    project_id: int = Field(index=True)
    milestone_id: Optional[int] = Field(default=None, index=True)

    source_filename: str = Field(default="")
    discipline: str = Field(default="", index=True)

    imported_at: datetime = Field(default_factory=datetime.utcnow)
    row_count: int = Field(default=0)


class CommentItem(SQLModel, table=True):
    __tablename__ = "comment_item"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)

    import_batch_id: int = Field(index=True)
    project_id: int = Field(index=True)
    milestone_id: Optional[int] = Field(default=None, index=True)

    discipline: str = Field(default="", index=True)
    sheet: str = Field(default="", index=True)
    subject: str = Field(default="")
    author: str = Field(default="", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    comment_text: str = Field(default="")

    page_index: Optional[int] = Field(default=None)
    markup_id: Optional[str] = Field(default=None)
    status_raw: Optional[str] = Field(default=None)

    # IMPORTANT: Import page uses this for dedupe
    source_row_hash: str = Field(default="", index=True)


class Comment(SQLModel, table=True):
    __tablename__ = "comment"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)

    project_id: int = Field(index=True)
    milestone_id: Optional[int] = Field(default=None, index=True)

    discipline: str = Field(default="", index=True)
    sheet: str = Field(default="", index=True)
    subject: str = Field(default="")
    author: str = Field(default="", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    comment_text: str = Field(default="")

    status: str = Field(default="Open", index=True)
    tracked: bool = Field(default=False, index=True)
    owner: str = Field(default="")
    due_date: Optional[date] = Field(default=None)

    tag: str = Field(default="", index=True)
    risk: str = Field(default="", index=True)
    required_response: str = Field(default="")
