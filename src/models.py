# src/models.py
from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlmodel import SQLModel, Field


class Project(SQLModel, table=True):
    __tablename__ = "project"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    is_active: bool = Field(default=True, index=True)  # ← add this
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Milestone(SQLModel, table=True):
    __tablename__ = "milestone"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)

    name: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Comment(SQLModel, table=True):
    __tablename__ = "comment"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)

    project_id: int = Field(index=True)
    milestone_id: Optional[int] = Field(default=None, index=True)

    discipline: str = Field(default="", index=True)   # A, E, M, etc.
    sheet: str = Field(default="", index=True)        # Page Label
    subject: str = Field(default="")                  # Markup subject/type
    author: str = Field(default="", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    comment_text: str = Field(default="")

    # workflow fields
    status: str = Field(default="Open", index=True)
    tracked: bool = Field(default=False, index=True)
    owner: str = Field(default="")
    due_date: Optional[date] = Field(default=None)

    # AI / categorization fields
    tag: str = Field(default="", index=True)          # RFI/COORD/etc.
    risk: str = Field(default="", index=True)         # LOW/MED/HIGH
    required_response: str = Field(default="")
