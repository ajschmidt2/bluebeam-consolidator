import json

import streamlit as st
from sqlmodel import select

from src.auth import require_login
from src.db import init_db, session_scope
from src.import_bluebeam import infer_mapping, load_bluebeam_csv, row_fingerprint
from src.models import Project, Milestone, ImportBatch, CommentItem
from src.settings import get_setting, set_setting

st.set_page_config(page_title="Import", layout="wide")
init_db()
require_login()

st.title("Import Bluebeam Markups Summary CSV")

with session_scope() as s:
    projects = s.exec(select(Project).where(Project.is_active == True).order_by(Project.name)).all()

if not projects:
    st.warning("Create a project first (Projects page).")
    st.stop()

project_map = {f"{p.name} (#{p.id})": p.id for p in projects}
project_label = st.selectbox("Project", list(project_map.keys()))
project_id = project_map[project_label]

with session_scope() as s:
    miles = s.exec(select(Milestone).where(Milestone.project_id == project_id).order_by(Milestone.created_at.desc())).all()

if not miles:
    st.warning("Add a milestone for this project first (Projects page).")
    st.stop()

milestone_map = {f"{m.name} (#{m.id})": m.id for m in miles}
milestone_label = st.selectbox("Milestone", list(milestone_map.keys()))
milestone_id = milestone_map[milestone_label]

uploaded = st.file_uploader("Upload Bluebeam CSV", type=["csv"]) 

st.caption("Tip: Export from Bluebeam using Markups List → Summary → CSV.")

if not uploaded:
    st.stop()

file_bytes = uploaded.getvalue()

# Load quickly to infer mapping
temp_df = None
try:
    import pandas as pd
    temp_df = pd.read_csv(pd.io.common.BytesIO(file_bytes), nrows=5)
except Exception as e:
    st.error(f"Could not read CSV: {e}")
    st.stop()

cols = list(temp_df.columns)

saved_mapping_json = get_setting("column_mapping")
saved_mapping = json.loads(saved_mapping_json) if saved_mapping_json else None

default_map = infer_mapping(cols)

st.subheader("Column mapping")

col1, col2, col3 = st.columns(3)

sheet_col = col1.selectbox("Sheet / Page Label column", ["(none)"] + cols, index=(["(none)"] + cols).index(default_map["sheet"]) if default_map["sheet"] in cols else 0)
author_col = col2.selectbox("Author column", ["(none)"] + cols, index=(["(none)"] + cols).index(default_map["author"]) if default_map["author"] in cols else 0)
date_col = col3.selectbox("Created date column", ["(none)"] + cols, index=(["(none)"] + cols).index(default_map["created_at"]) if default_map["created_at"] in cols else 0)

col4, col5 = st.columns(2)
subject_col = col4.selectbox("Subject / Type column", ["(none)"] + cols, index=(["(none)"] + cols).index(default_map["subject"]) if default_map["subject"] in cols else 0)
comment_col = col5.selectbox("Comment text column", ["(none)"] + cols, index=(["(none)"] + cols).index(default_map["comment"]) if default_map["comment"] in cols else 0)

mapping = {
    "sheet": "" if sheet_col == "(none)" else sheet_col,
    "author": "" if author_col == "(none)" else author_col,
    "created_at": "" if date_col == "(none)" else date_col,
    "subject": "" if subject_col == "(none)" else subject_col,
    "comment": "" if comment_col == "(none)" else comment_col,
}

if st.button("Save this mapping for future imports"):
    set_setting("column_mapping", json.dumps(mapping))
    st.success("Saved")

st.divider()

st.subheader("Preview")
preview_df = load_bluebeam_csv(file_bytes, mapping)
st.dataframe(preview_df.head(25), use_container_width=True)

st.subheader("Import")
tracked_default = st.checkbox("Default imported items to Tracked = True", value=False)

if st.button("Import to database", type="primary"):
    with session_scope() as s:
        batch = ImportBatch(
            project_id=project_id,
            milestone_id=milestone_id,
            source_filename=uploaded.name,
            row_count=len(preview_df),
        )
        s.add(batch)
        s.commit()
        s.refresh(batch)

        inserted = 0
        skipped = 0

        for _, r in preview_df.iterrows():
            sheet = str(r.get("sheet", "") or "").strip()
            author = str(r.get("author", "") or "").strip()
            subject = str(r.get("subject", "") or "").strip() or None
            comment_text = str(r.get("comment_text", "") or "").strip()
            created_at = r.get("created_at", None)

            if not comment_text:
                continue

            fp = row_fingerprint(project_id, milestone_id, sheet, author, created_at, comment_text)
            exists = s.exec(select(CommentItem).where(CommentItem.source_row_hash == fp)).first()
            if exists:
                skipped += 1
                continue

            item = CommentItem(
                project_id=project_id,
                milestone_id=milestone_id,
                import_batch_id=batch.id,
                discipline=str(r.get("discipline", "") or "").strip(),
                sheet=sheet,
                subject=subject,
                author=author or None,
                created_at=created_at,
                comment_text=comment_text,
                status="Open",
                tracked=tracked_default,
                source_file=uploaded.name,
                source_row_hash=fp,
            )
            s.add(item)
            inserted += 1

        s.commit()

    st.success(f"Imported {inserted} items. Skipped {skipped} duplicates.")
    st.info("Go to the Comments Dashboard page to triage, assign, and export.")
