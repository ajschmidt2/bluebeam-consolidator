from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Dict, Optional, Tuple, List

import pandas as pd
from dateutil import parser as dtparser


DEFAULT_COLUMN_ALIASES = {
    "sheet": ["page label", "pagelabel", "sheet", "sheet number", "page"],
    "author": ["author", "creator", "user"],
    "created_at": ["date", "creation date", "created", "created at"],
    "subject": ["subject", "type", "markup", "tool"],
    "comment": ["comment", "contents", "text", "note", "comment text"],
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).strip().lower())


def infer_mapping(columns: List[str]) -> Dict[str, Optional[str]]:
    """Infer a best-effort column mapping from a Bluebeam Markups Summary CSV."""
    cols_norm = {_norm(c): c for c in columns}

    def pick(candidates: List[str]) -> Optional[str]:
        for cand in candidates:
            cand_n = _norm(cand)
            if cand_n in cols_norm:
                return cols_norm[cand_n]
        # partial match fallback
        for cand in candidates:
            cand_n = _norm(cand)
            for cn, orig in cols_norm.items():
                if cand_n in cn:
                    return orig
        return None

    return {
        "sheet": pick(DEFAULT_COLUMN_ALIASES["sheet"]),
        "author": pick(DEFAULT_COLUMN_ALIASES["author"]),
        "created_at": pick(DEFAULT_COLUMN_ALIASES["created_at"]),
        "subject": pick(DEFAULT_COLUMN_ALIASES["subject"]),
        "comment": pick(DEFAULT_COLUMN_ALIASES["comment"]),
    }


def parse_created_at(value) -> Optional[datetime]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        # dateutil handles a lot of formats
        return dtparser.parse(s, fuzzy=True)
    except Exception:
        return None


def infer_discipline_from_sheet(sheet: str) -> str:
    if not sheet:
        return ""
    # Common sheet prefixes (A, C, S, M, P, E, FP, etc.)
    s = sheet.strip().upper()
    # If sheet has spaces like "E101 - LIGHTING PLAN", take token before space
    token = s.split()[0]
    # If token has dash or dot, take leading alpha group
    m = re.match(r"^([A-Z]{1,3})", token)
    return m.group(1) if m else token[:1]


def row_fingerprint(
    project_id: int,
    milestone_id: int,
    sheet: str,
    author: str,
    created_at: Optional[datetime],
    comment_text: str,
) -> str:
    base = "|".join(
        [
            str(project_id),
            str(milestone_id),
            (sheet or "").strip().upper(),
            (author or "").strip().lower(),
            (created_at.isoformat() if created_at else ""),
            (comment_text or "").strip(),
        ]
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def load_bluebeam_csv(
    file_bytes: bytes,
    mapping: Dict[str, str],
) -> pd.DataFrame:
    df = pd.read_csv(pd.io.common.BytesIO(file_bytes))

    # Normalize expected columns
    col_sheet = mapping.get("sheet")
    col_author = mapping.get("author")
    col_created = mapping.get("created_at")
    col_subject = mapping.get("subject")
    col_comment = mapping.get("comment")

    out = pd.DataFrame()
    out["sheet"] = df[col_sheet] if col_sheet in df.columns else ""
    out["author"] = df[col_author] if col_author in df.columns else ""
    out["created_at"] = df[col_created] if col_created in df.columns else ""
    out["subject"] = df[col_subject] if col_subject in df.columns else ""
    out["comment_text"] = df[col_comment] if col_comment in df.columns else ""

    # Clean
    out["sheet"] = out["sheet"].astype(str).fillna("").str.strip()
    out["author"] = out["author"].astype(str).fillna("").str.strip()
    out["subject"] = out["subject"].astype(str).fillna("").str.strip()
    out["comment_text"] = out["comment_text"].astype(str).fillna("").str.strip()

    out["created_at"] = out["created_at"].apply(parse_created_at)
    out["discipline"] = out["sheet"].apply(infer_discipline_from_sheet)

    return out
