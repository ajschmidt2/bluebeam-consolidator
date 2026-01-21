from datetime import date

import streamlit as st
from sqlmodel import select

from src.auth import require_login
from src.db import init_db, session_scope
from src.models import Project, Milestone, CommentItem

st.set_page_config(page_title="Dashboard", layout="wide")
init_db()
require_login()

st.title("Comments Dashboard")

with session_scope() as s:
    projects = s.exec(select(Project).order_by(Project.is_active.desc(), Project.name)).all()

if not projects:
    st.warning("Create a project first.")
    st.stop()

proj_map = {f"{p.name} (#{p.id})": p.id for p in projects}
proj_label = st.selectbox("Project", list(proj_map.keys()))
project_id = proj_map[proj_label]

with session_scope() as s:
    miles = s.exec(select(Milestone).where(Milestone.project_id == project_id).order_by(Milestone.created_at.desc())).all()

milestone_id = None
if miles:
    mile_map = {"(All milestones)": None, **{f"{m.name} (#{m.id})": m.id for m in miles}}
    mile_label = st.selectbox("Milestone", list(mile_map.keys()))
    milestone_id = mile_map[mile_label]

with session_scope() as s:
    q = select(CommentItem).where(CommentItem.project_id == project_id)
    if milestone_id:
        q = q.where(CommentItem.milestone_id == milestone_id)

    items_all = s.exec(q).all()

if not items_all:
    st.info("No comments yet. Import a Bluebeam CSV first.")
    st.stop()

# Sidebar filters
st.sidebar.markdown("### Filters")

def uniq(vals):
    return sorted({v for v in vals if v not in (None, "")})

statuses = ["(All)"] + uniq([i.status for i in items_all])
disciplines = ["(All)"] + uniq([i.discipline for i in items_all])
authors = ["(All)"] + uniq([i.author for i in items_all])
sheets = ["(All)"] + uniq([i.sheet for i in items_all])

f_status = st.sidebar.selectbox("Status", statuses)
f_disc = st.sidebar.selectbox("Discipline", disciplines)
f_author = st.sidebar.selectbox("Author", authors)
f_sheet = st.sidebar.selectbox("Sheet", sheets)

f_tracked = st.sidebar.selectbox("Tracked", ["(All)", "Tracked only", "Untracked only"])
text_search = st.sidebar.text_input("Search text", placeholder="keywords...")

filtered = items_all
if f_status != "(All)":
    filtered = [i for i in filtered if i.status == f_status]
if f_disc != "(All)":
    filtered = [i for i in filtered if i.discipline == f_disc]
if f_author != "(All)":
    filtered = [i for i in filtered if (i.author or "") == f_author]
if f_sheet != "(All)":
    filtered = [i for i in filtered if i.sheet == f_sheet]
if f_tracked == "Tracked only":
    filtered = [i for i in filtered if i.tracked]
elif f_tracked == "Untracked only":
    filtered = [i for i in filtered if not i.tracked]
if text_search.strip():
    t = text_search.strip().lower()
    filtered = [i for i in filtered if t in (i.comment_text or "").lower() or t in (i.required_response or "").lower()]

st.write(f"Showing **{len(filtered)}** of **{len(items_all)}** items")

# Bulk actions
st.subheader("Bulk actions")
colA, colB, colC, colD, colE = st.columns([1.2,1.2,1.2,1.2,1.2])
new_status = colA.selectbox("Set status", ["(no change)", "Open", "Needs Response", "In Progress", "Implemented", "Closed"])
new_owner = colB.text_input("Set owner", placeholder="(no change)")
new_due = colC.date_input("Set due date", value=None)
new_tags = colD.text_input("Add tags", placeholder="comma-separated")
set_tracked = colE.selectbox("Tracked", ["(no change)", "Set tracked", "Set untracked"])

st.caption("Select rows below, then apply bulk changes.")

# Table with selection
import pandas as pd

rows = []
for it in filtered:
    rows.append({
        "Select": False,
        "ID": it.id,
        "Tracked": it.tracked,
        "Status": it.status,
        "Owner": it.owner or "",
        "Due": it.due_date.isoformat() if it.due_date else "",
        "Disc": it.discipline,
        "Sheet": it.sheet,
        "Author": it.author or "",
        "Comment": it.comment_text,
        "Required Response": it.required_response or "",
        "Tags": it.tags or "",
    })

df = pd.DataFrame(rows)

edited = st.data_editor(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Select": st.column_config.CheckboxColumn(required=False),
        "Comment": st.column_config.TextColumn(width="large"),
        "Required Response": st.column_config.TextColumn(width="large"),
    },
    disabled=[c for c in df.columns if c not in ("Select",)],
)

selected_ids = edited.loc[edited["Select"] == True, "ID"].tolist() if not edited.empty else []

if st.button("Apply bulk updates", type="primary", disabled=(len(selected_ids) == 0)):
    with session_scope() as s:
        for cid in selected_ids:
            it = s.get(CommentItem, int(cid))
            if not it:
                continue
            if new_status != "(no change)":
                it.status = new_status
            if new_owner.strip():
                it.owner = new_owner.strip()
            if isinstance(new_due, date):
                it.due_date = new_due
            if new_tags.strip():
                # merge tags
                existing = set([t.strip() for t in (it.tags or "").split(",") if t.strip()])
                added = set([t.strip() for t in new_tags.split(",") if t.strip()])
                it.tags = ", ".join(sorted(existing | added))
            if set_tracked == "Set tracked":
                it.tracked = True
            elif set_tracked == "Set untracked":
                it.tracked = False
            s.add(it)
        s.commit()
    st.success(f"Updated {len(selected_ids)} items")
    st.rerun()

st.divider()

st.subheader("Edit a single item")
edit_id = st.number_input("Comment ID", min_value=1, step=1)

with session_scope() as s:
    item = s.get(CommentItem, int(edit_id)) if edit_id else None

if item and item.project_id == project_id and (not milestone_id or item.milestone_id == milestone_id):
    st.write(f"**Sheet:** {item.sheet}  |  **Discipline:** {item.discipline}  |  **Status:** {item.status}")
    st.write(f"**Comment:** {item.comment_text}")

    c1, c2, c3 = st.columns([1.2,1.2,1.2])
    item.status = c1.selectbox("Status", ["Open", "Needs Response", "In Progress", "Implemented", "Closed"], index=["Open","Needs Response","In Progress","Implemented","Closed"].index(item.status) if item.status in ["Open","Needs Response","In Progress","Implemented","Closed"] else 0)
    item.owner = c2.text_input("Owner", value=item.owner or "") or None
    item.tracked = c3.checkbox("Tracked", value=item.tracked)

    item.tags = st.text_input("Tags (comma-separated)", value=item.tags or "") or None
    rr = st.text_area("Required response", value=item.required_response or "", height=120)
    item.required_response = rr.strip() or None

    if st.button("Save item"):
        with session_scope() as s:
            it2 = s.get(CommentItem, item.id)
            it2.status = item.status
            it2.owner = item.owner
            it2.tracked = item.tracked
            it2.tags = item.tags
            it2.required_response = item.required_response
            s.add(it2)
            s.commit()
        st.success("Saved")
        st.rerun()
else:
    st.caption("Enter an ID shown in the table above to edit a single item.")
from src.llm import triage_comment_cached

if st.button("AI: Triage selected"):
    for row in selected_rows:
        result = triage_comment_cached(
            comment_text=row["comment_text"],
            sheet=row["sheet"],
            discipline=row["discipline"],
            milestone=milestone_name,
        )
        # apply to DB (you likely already have an update_comment(...) helper)
        update_comment(
            comment_id=row["id"],
            tracked=result["track"],
            tags=result["tag"],
            risk=result["risk"],
            required_response=result["required_response"],
        )
    st.success("AI triage applied.")
