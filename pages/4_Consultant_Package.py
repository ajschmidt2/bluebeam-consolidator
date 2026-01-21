import streamlit as st
from sqlmodel import select

from src.auth import require_login
from src.db import init_db, session_scope
from src.exporters import build_consultant_package, comments_to_dataframe
from src.models import Project, Milestone, CommentItem

st.set_page_config(page_title="Consultant Package", layout="wide")
init_db()
require_login()

st.title("Consultant Response Package")

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
    items = s.exec(q).all()

if not items:
    st.info("No items yet.")
    st.stop()

# Filters
st.subheader("Filter")

def uniq(vals):
    return sorted({v for v in vals if v not in (None, "")})

disciplines = ["(All)"] + uniq([i.discipline for i in items])
statuses = ["(All)"] + uniq([i.status for i in items])

c1, c2, c3 = st.columns([1.2,1.2,1.2])
f_disc = c1.selectbox("Discipline", disciplines)
f_status = c2.selectbox("Status", statuses, index=statuses.index("Needs Response") if "Needs Response" in statuses else 0)
tracked_only = c3.checkbox("Tracked only", value=True)

filtered = items
if f_disc != "(All)":
    filtered = [i for i in filtered if i.discipline == f_disc]
if f_status != "(All)":
    filtered = [i for i in filtered if i.status == f_status]
if tracked_only:
    filtered = [i for i in filtered if i.tracked]

st.write(f"Items in package: **{len(filtered)}**")

header = st.text_area(
    "Header / intro (optional)",
    value="Please review and respond to the following items. For each, provide your proposed resolution and indicate whether drawings/specs will be revised.",
    height=90,
)

package_text = build_consultant_package(filtered, header=header)

st.subheader("Package text")
st.code(package_text, language="text")

st.download_button(
    "Download package as .txt",
    data=package_text.encode("utf-8"),
    file_name="consultant_response_package.txt",
    mime="text/plain",
)

st.subheader("Export as CSV")
import pandas as pd

df = comments_to_dataframe(filtered)
st.dataframe(df, use_container_width=True)

st.download_button(
    "Download CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="consultant_package.csv",
    mime="text/csv",
)
