# pages/3_Comments_Dashboard.py
from __future__ import annotations

import datetime as dt
from typing import Optional, List

import pandas as pd
import streamlit as st
from sqlmodel import Session, select

from src.db import get_engine
from src.models import Project, Milestone, Comment

st.set_page_config(page_title="Comments Dashboard", layout="wide")

# -----------------------------
# Optional AI import (safe)
# -----------------------------
triage_comment_cached = None
_ai_import_error = None
try:
    from src.llm import triage_comment_cached  # type: ignore
except Exception as e:
    triage_comment_cached = None
    _ai_import_error = str(e)


# -----------------------------
# DB helpers
# -----------------------------
def _get_projects() -> list[Project]:
    with Session(get_engine()) as s:
        return list(s.exec(select(Project).order_by(Project.name)))


def _get_milestones(project_id: Optional[int]) -> list[Milestone]:
    if not project_id:
        return []
    with Session(get_engine()) as s:
        stmt = (
            select(Milestone)
            .where(Milestone.project_id == project_id)
            .order_by(Milestone.created_at.desc())
        )
        return list(s.exec(stmt))


def _load_comments(
    project_id: Optional[int],
    milestone_id: Optional[int],
    discipline: str,
    status: str,
    tracked_filter: str,
    search: str,
) -> pd.DataFrame:
    with Session(get_engine()) as s:
        stmt = select(Comment)

        if project_id:
            stmt = stmt.where(Comment.project_id == project_id)
        if milestone_id:
            stmt = stmt.where(Comment.milestone_id == milestone_id)

        if discipline != "All":
            stmt = stmt.where(Comment.discipline == discipline)

        if status != "All":
            stmt = stmt.where(Comment.status == status)

        if tracked_filter != "All":
            stmt = stmt.where(Comment.tracked == (tracked_filter == "Tracked"))

        if search.strip():
            q = f"%{search.strip()}%"
            stmt = stmt.where(
                (Comment.comment_text.ilike(q))
                | (Comment.sheet.ilike(q))
                | (Comment.author.ilike(q))
                | (Comment.tag.ilike(q))
                | (Comment.required_response.ilike(q))
            )

        stmt = stmt.order_by(Comment.created_at.desc())

        rows = list(s.exec(stmt))

    # Build a dataframe with ALL columns we care about, including AI outputs
    data = []
    for r in rows:
        data.append(
            {
                "select": False,  # checkbox column for selection
                "id": r.id,
                "discipline": r.discipline or "",
                "sheet": r.sheet or "",
                "subject": r.subject or "",
                "author": r.author or "",
                "created_at": r.created_at.isoformat(sep=" ", timespec="minutes") if r.created_at else "",
                "status": r.status or "Open",
                "tracked": bool(r.tracked),
                "tag": r.tag or "",
                "risk": r.risk or "",
                "required_response": r.required_response or "",
                "owner": r.owner or "",
                "due_date": r.due_date.isoformat() if r.due_date else "",
                "comment_text": r.comment_text or "",
            }
        )
    return pd.DataFrame(data)


def _bulk_update(
    ids: list[int],
    *,
    status: Optional[str] = None,
    tracked: Optional[bool] = None,
    owner: Optional[str] = None,
    due_date: Optional[dt.date] = None,
    tag: Optional[str] = None,
    risk: Optional[str] = None,
) -> int:
    if not ids:
        return 0
    with Session(get_engine()) as s:
        stmt = select(Comment).where(Comment.id.in_(ids))
        rows = list(s.exec(stmt))
        for r in rows:
            if status is not None:
                r.status = status
            if tracked is not None:
                r.tracked = tracked
            if owner is not None:
                r.owner = owner
            if due_date is not None:
                r.due_date = due_date
            if tag is not None:
                r.tag = tag
            if risk is not None:
                r.risk = risk

        s.add_all(rows)
        s.commit()
    return len(ids)


def _apply_ai_to_selected(
    selected_rows: pd.DataFrame,
    milestone_name: str,
) -> int:
    """
    Calls AI per selected row and saves:
    tracked, tag, risk, required_response
    """
    if triage_comment_cached is None:
        raise RuntimeError("AI is not available. openai package/key may be missing.")

    updated = 0
    with Session(get_engine()) as s:
        for _, row in selected_rows.iterrows():
            comment_id = int(row["id"])
            obj = s.get(Comment, comment_id)
            if not obj:
                continue

            result = triage_comment_cached(
                comment_text=obj.comment_text or "",
                sheet=obj.sheet or "",
                discipline=obj.discipline or "",
                milestone=milestone_name or "",
            )

            # Save results into DB
            obj.tracked = bool(result.get("track", True))
            obj.tag = str(result.get("tag", "") or "")
            obj.risk = str(result.get("risk", "") or "")
            obj.required_response = str(result.get("required_response", "") or "")

            s.add(obj)
            updated += 1

        s.commit()

    return updated


# -----------------------------
# UI
# -----------------------------
st.title("Comments Dashboard")

projects = _get_projects()
project_name_to_id = {p.name: p.id for p in projects}

col_a, col_b, col_c, col_d, col_e = st.columns([2, 2, 1.5, 1.5, 2])

with col_a:
    project_name = st.selectbox(
        "Project",
        options=["(Select)"] + list(project_name_to_id.keys()),
        index=0,
    )
project_id = project_name_to_id.get(project_name)

milestones = _get_milestones(project_id)
milestone_name_to_id = {m.name: m.id for m in milestones}

with col_b:
    milestone_name = st.selectbox(
        "Milestone",
        options=["All"] + list(milestone_name_to_id.keys()),
        index=0,
        disabled=(project_id is None),
    )
milestone_id = None if milestone_name == "All" else milestone_name_to_id.get(milestone_name)

with col_c:
    discipline = st.selectbox(
        "Discipline",
        options=["All", "A", "S", "M", "E", "CIV", "FP", "OTHER"],
        index=0,
    )

with col_d:
    status = st.selectbox(
        "Status",
        options=["All", "Open", "Needs Response", "In Progress", "Implemented", "Closed"],
        index=0,
    )

with col_e:
    tracked_filter = st.selectbox(
        "Tracked Filter",
        options=["All", "Tracked", "Untracked"],
        index=0,
    )

search = st.text_input("Search (sheet, author, text, tag, required response)", value="")

df = _load_comments(
    project_id=project_id,
    milestone_id=milestone_id,
    discipline=discipline,
    status=status,
    tracked_filter=tracked_filter,
    search=search,
)

if df.empty:
    st.info("No comments found for the current filters.")
    st.stop()

# Keep edited table state across reruns
if "comments_editor" not in st.session_state:
    st.session_state["comments_editor"] = df

st.caption("Tip: Use the checkbox column to select comments, then use bulk actions or AI triage.")

edited_df = st.data_editor(
    df,
    key="comments_editor",
    use_container_width=True,
    hide_index=True,
    column_config={
        "select": st.column_config.CheckboxColumn("Select", help="Select rows for bulk actions / AI triage"),
        "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
        "comment_text": st.column_config.TextColumn("Comment", width="large"),
        "required_response": st.column_config.TextColumn("Required Response", width="large"),
        "tracked": st.column_config.CheckboxColumn("Tracked"),
    },
    disabled=["id"],  # allow editing most fields directly if you want
)

selected_rows = edited_df[edited_df["select"] == True].copy()

# -----------------------------
# Bulk actions panel
# -----------------------------
st.subheader("Bulk Actions")

b1, b2, b3, b4, b5, b6 = st.columns([1.2, 1.2, 1.2, 1.2, 1.2, 2])

with b1:
    new_status = st.selectbox("Set Status", ["(no change)", "Open", "Needs Response", "In Progress", "Implemented", "Closed"])
with b2:
    new_tracked = st.selectbox("Set Tracked", ["(no change)", "Tracked", "Untracked"])
with b3:
    new_owner = st.text_input("Set Owner", value="", placeholder="e.g., Electrical Engineer")
with b4:
    new_due = st.date_input("Set Due Date", value=None)
with b5:
    new_tag = st.selectbox("Set Tag", ["(no change)", "RFI", "DECISION", "COORD", "CODE", "COST", "SCHED", "QA", "OTHER"])
with b6:
    new_risk = st.selectbox("Set Risk", ["(no change)", "LOW", "MED", "HIGH"])

apply_bulk = st.button("Apply Bulk Changes", type="primary", use_container_width=True)

if apply_bulk:
    if selected_rows.empty:
        st.warning("Select one or more comments first (checkbox column).")
    else:
        ids = selected_rows["id"].astype(int).tolist()

        _status = None if new_status == "(no change)" else new_status
        _tracked = None
        if new_tracked == "Tracked":
            _tracked = True
        elif new_tracked == "Untracked":
            _tracked = False

        _owner = None if not new_owner.strip() else new_owner.strip()
        _due = None
        if isinstance(new_due, dt.date):
            _due = new_due

        _tag = None if new_tag == "(no change)" else new_tag
        _risk = None if new_risk == "(no change)" else new_risk

        count = _bulk_update(
            ids,
            status=_status,
            tracked=_tracked,
            owner=_owner,
            due_date=_due,
            tag=_tag,
            risk=_risk,
        )
        st.success(f"Updated {count} comments.")
        st.rerun()

# -----------------------------
# AI Triage panel
# -----------------------------
st.subheader("AI Assist")

if triage_comment_cached is None:
    st.info(
        "AI features are disabled. "
        "Fix by: (1) add `openai>=1.0.0` to requirements.txt, "
        "(2) add OPENAI_API_KEY to Streamlit Secrets, then reboot the app."
    )
    if _ai_import_error:
        with st.expander("AI import error (for troubleshooting)"):
            st.code(_ai_import_error)
else:
    if "OPENAI_API_KEY" not in st.secrets:
        st.warning("OPENAI_API_KEY is missing in Streamlit Secrets. Add it to enable AI calls.")
    else:
        ai_col1, ai_col2 = st.columns([1.5, 3])
        with ai_col1:
            run_ai = st.button("AI: Triage selected", use_container_width=True)
        with ai_col2:
            st.caption("AI triage fills Tracked, Tag, Risk, and Required Response for the selected rows.")

        if run_ai:
            if selected_rows.empty:
                st.warning("Select one or more comments first (checkbox column).")
            else:
                if milestone_name == "All":
                    milestone_for_ai = ""
                else:
                    milestone_for_ai = milestone_name

                with st.spinner("Running AI triage on selected comments..."):
                    updated = _apply_ai_to_selected(selected_rows, milestone_for_ai)

                st.success(f"AI triage applied to {updated} comments.")
                st.rerun()
