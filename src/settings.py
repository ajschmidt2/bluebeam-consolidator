# src/settings.py
from __future__ import annotations

from sqlmodel import select

from src.db import session_scope
from src.models import AppSetting


def get_setting(key: str, default: str = "") -> str:
    with session_scope() as s:
        row = s.get(AppSetting, key)
        return row.value if row else default


def set_setting(key: str, value: str) -> None:
    with session_scope() as s:
        row = s.get(AppSetting, key)
        if row:
            row.value = value
        else:
            row = AppSetting(key=key, value=value)
        s.add(row)
