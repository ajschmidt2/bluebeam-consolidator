from __future__ import annotations

from typing import Optional

from sqlmodel import select

from .db import session_scope
from .models import AppSetting


def get_setting(key: str) -> Optional[str]:
    with session_scope() as s:
        row = s.exec(select(AppSetting).where(AppSetting.key == key)).first()
        return row.value if row else None


def set_setting(key: str, value: str) -> None:
    with session_scope() as s:
        row = s.exec(select(AppSetting).where(AppSetting.key == key)).first()
        if row:
            row.value = value
        else:
            row = AppSetting(key=key, value=value)
            s.add(row)
        s.commit()
