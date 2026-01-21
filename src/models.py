from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlmodel import SQLModel, Field


class Project(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    client: Optional[str] = None
    location: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Milestone(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    name: str
    target_date: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ImportBatch(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    milestone_id: int = Field(index=True)
    source_filename: str
    imported_at: datetime = Field(default_factory=datetime.utcnow)
    row_count: int = 0


class CommentItem(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)

    project_id: int = Field(index=True)
    milestone_id: int = Field(index=True)
    import_batch_id: Optional[int] = Field(default=None, index=True)

    discipline: str = Field(index=True, default="")
    sheet: str = Field(index=True, default="")
    subject: Optional[str] = Field(default=None, index=True)

    author: Optional[str] = Field(default=None, index=True)
    created_at: Optional[datetime] = Field(default=None, index=True)

    comment_text: str
    required_response: Optional[str] = None

    status: str = Field(index=True, default="Open")
    owner: Optional[str] = Field(default=None, index=True)
    due_date: Optional[date] = Field(default=None, index=True)

    tags: Optional[str] = Field(default=None, index=True)  # comma-separated

    tracked: bool = Field(default=False, index=True)

    source_file: Optional[str] = None
    source_row_hash: str = Field(index=True)

    created_db_at: datetime = Field(default_factory=datetime.utcnow)


class AppSetting(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    value: str
