# pages/2_Import_Bluebeam_CSV.py
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime
from typing import Any, Dict, Optional

import streamlit as st
from sqlmodel import select

from src.auth import require_login
from src.db import init_db, session_scope
from src.models import Project, Milestone, ImportBatch, CommentItem, Comment
from src.settings import get_setting, set_setting

st.set_page_config(page_title="Import Bluebeam CSV", layout="wide")
init_db()
require_login()

st.title("Import")

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def _first_nonempty(d: Dict[str, Any], keys: list[str], default: str = "") -> str:
    for k in keys:
        v = d.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return default


def _parse_datetime(s: str) -> Optional[datetime]:
    s = (s or "").strip()
    if not s:
        return None
    # Try a few common Bluebeam-ish formats
    fmts = [
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    ]
    for f in fmts:
        try:
            return datetime.strptime(s, f)
        except Exception:
            pass
    # last resort: try ISO-ish
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def make_row_hash(row: Dict[str, Any]) -> str:
    """
    Stable, non-empty fingerprint.
    Prevents fp="" which causes everything to be treated as duplicate.
    """
    payload = {
        "sheet": _first_nonempty(row, ["sheet", "Sheet", "Page Label", "Page", "PageLabel"]),
        "author": _first_nonempty(row, ["author", "Author", "Created By", "Creator"]),
        "subject": _first_nonempty(row, ["subject", "Subject", "Type", "Markup Type"]),
        "created": _first_nonempty(row, ["created_at", "Created", "Date", "Creation Date", "Timestamp"]),
        "comment": _first_nonempty(row, ["comment_text", "Comment", "Contents", "Text", "Comments", "Note"]),
        "markup_id": _first_nonempty(row, ["markup_id", "Markup ID", "ID", "Annotation ID"]),
    }

    # If everything is blank, hash the whole row to avoid identical hashes
    if not any(payload.values()):
        payload = row

    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ------------------------------------------------------------
# UI: Project / Milestone selection
# ------------------------------------------------------------
with session_scope() as s:
    projects = s.exec(select(Project).order_by(Project.is_active.desc(), Project.name)).all()

if not projects:
    st.warning("Create a project first on the Projects page.")
    st.stop()

proj_opts = {f"{p.name} (#{p.id})": p.id for p in projects}
proj_label = st.selectbox("Project", list(proj_opts.keys()))
project_id = proj_opts[proj_label]

with session_scope() as s:
    miles = s.exec(
        select(Milestone).where(Milestone.project_id == project_id).order_by(Milestone.created_at.desc())
    ).all()

mile_opts = {"(None)": None} | {f"{m.name} (#{m.id})": m.id for m in miles}
mile_label = st.selectbox("Milestone (optional)", list(mile_opts.keys()))
milestone_id = mile_opts[mile_label]

discipline = st.selectbox("Discipline", ["A", "S", "M", "E", "CIV", "FP", "OTHER"], index=3)

default_tracked = st.checkbox("Default imported items to Tracked = True", value=(get_setting("default_tracked", "true") == "true"))

set_setting("default_tracked", "true" if default_tracked else "false")

uploaded = st.file_uploader("Upload Bluebeam CSV", type=["csv"])

if not uploaded:
    st.info("Upload a Bluebeam CSV export to import markups/comments.")
    st.stop()

# ------------------------------------------------------------
# Read CSV
# ------------------------------------------------------------
raw_bytes = uploaded.getvalue()
text = raw_bytes.decode("utf-8", errors="replace")

# Use csv.DictReader to map columns to dict keys.
reader = csv.DictReader(io.StringIO(text))
rows = [dict(r) for r in reader]

st.write(f"Rows found in CSV: **{len(rows)}**")

if len(rows) == 0:
    st.error("No rows found. Is this a valid CSV export?")
    st.stop()

# Preview first 10 rows
with st.expander("Preview first 10 rows"):
    st.dataframe(rows[:10], use_container_width=True, hide_index=True)

# ------------------------------------------------------------
# Import
# ------------------------------------------------------------
if st.button("Import to database", type="primary"):
    imported = 0
    skipped = 0

    with session_scope() as s:
        batch = ImportBatch(
            project_id=project_id,
            milestone_id=milestone_id,
            source_filename=uploaded.name,
            discipline=discipline,
            row_count=len(rows),
        )
        s.add(batch)
        s.flush()  # get batch.id without closing session
        batch_id = batch.id

        for r in rows:
            # Build the core fields with flexible column names
            sheet = _first_nonempty(r, ["Page Label", "Page", "Sheet", "sheet"])
            author = _first_nonempty(r, ["Author", "Created By", "Creator", "author"])
            subject = _first_nonempty(r, ["Subject", "Type", "Markup Type", "subject"])
            comment_text = _first_nonempty(r, ["Comment", "Contents", "Text", "Comments", "Note", "comment_text"])
            markup_id = _first_nonempty(r, ["Markup ID", "ID", "Annotation ID", "markup_id"])
            created_str = _first_nonempty(r, ["Created", "Date", "Creation Date", "Timestamp", "created_at"])
            created_at = _parse_datetime(created_str) or datetime.utcnow()

            # Fingerprint for dedupe
            fp = make_row_hash(
                {
                    "sheet": sheet,
                    "author": author,
                    "subject": subject,
                    "comment_text": comment_text,
                    "markup_id": markup_id,
                    "created_at": created_str,
                }
            )

            # Check duplicates using source_row_hash
            exists = s.exec(
                select(CommentItem).where(CommentItem.source_row_hash == fp)
            ).first()

            if exists:
                skipped += 1
                continue

            item = CommentItem(
                import_batch_id=batch_id,
                project_id=project_id,
                milestone_id=milestone_id,
                discipline=discipline,
                sheet=sheet,
                subject=subject,
                author=author,
                created_at=created_at,
                comment_text=comment_text,
                markup_id=markup_id or None,
                status_raw=_first_nonempty(r, ["Status", "State", "status_raw"]) or None,
                source_row_hash=fp,
            )
            s.add(item)

            # Also insert into the working Comment table so it appears in the dashboard
            c = Comment(
                project_id=project_id,
                milestone_id=milestone_id,
                discipline=discipline,
                sheet=sheet,
                subject=subject,
                author=author,
                created_at=created_at,
                comment_text=comment_text,
                status="Open",
                tracked=bool(default_tracked),
            )
            s.add(c)

            imported += 1

    st.success(f"Imported {imported} items. Skipped {skipped} duplicates.")
    st.caption("If you expected fewer items, your CSV likely contains extra non-comment rows. Use filters next if needed.")
    st.rerun()
