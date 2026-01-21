# pages/1_Projects.py
from __future__ import annotations

from datetime import date
import streamlit as st
from sqlmodel import select

from src.auth import require_login
from src.db import init_db, session_scope
from src.models import Project, Milestone

st.set_page_config(page_title="Projects", layout="wide")
init_db()
require_login()

st.title("Projects & Milestones")

# -----------------------------
# Create Project
# -----------------------------
with st.expander("➕ Create a project", expanded=True):
    c1, c2, c3 = st.columns([2, 2, 2])
    name = c1.text_input("Project name")
    client = c2.text_input("Client (optional)")
    location = c3.text_input("Location (optional)")

    if st.button("Create project", type="primary"):
        if not name.strip():
            st.error("Project name is required")
        else:
            with session_scope() as s:
                p = Project(
                    name=name.strip(),
                    client=(client.strip() or None),
                    location=(location.strip() or None),
                    is_active=True,
                )
                s.add(p)
            st.success("Project created")
            st.rerun()

# -----------------------------
# Load projects (convert to plain dicts BEFORE session closes)
# -----------------------------
with session_scope() as s:
    rows = s.exec(
        select(Project).order_by(Project.is_active.desc(), Project.name)
    ).all()

projects = [
    {
        "id": p.id,
        "name": p.name,
        "client": getattr(p, "client", None),
        "location": getattr(p, "location", None),
        "is_active": bool(getattr(p, "is_active", True)),
    }
    for p in rows
]

if not projects:
    st.warning("Create your first project above.")
    st.stop()

project_opts = {f"{p['name']} (#{p['id']})": p["id"] for p in projects}
selected_label = st.selectbox("Select project", list(project_opts.keys()))
project_id = project_opts[selected_label]

# Get selected project dict (no DB object usage = no DetachedInstanceError)
proj = next((p for p in projects if p["id"] == project_id), None)
if not proj:
    st.error("Selected project not found. Try refreshing.")
    st.stop()

# -----------------------------
# Project details
# -----------------------------
st.subheader("Project details")
colA, colB, colC, colD = st.columns([2, 2, 2, 1])
colA.write(f"**Name:** {proj['name']}")
colB.write(f"**Client:** {proj['client'] or '—'}")
colC.write(f"**Location:** {proj['location'] or '—'}")
colD.write(f"**Active:** {proj['is_active']}")

if st.button("Toggle Active / Archived"):
    with session_scope() as s:
        p = s.get(Project, project_id)
        if p is None:
            st.error("Could not load project to update.")
            st.stop()
        p.is_active = not bool(getattr(p, "is_active", True))
        s.add(p)
    st.rerun()

st.divider()

# -----------------------------
# Milestones
# -----------------------------
st.subheader("Milestones")
with st.expander("➕ Add milestone", expanded=False):
    m_name = st.text_input("Milestone name (e.g., 100% DD Review)")
    m_date = st.date_input("Target date (optional)", value=None)

    if st.button("Add milestone"):
        if not m_name.strip():
            st.error("Milestone name is required")
        else:
            with session_scope() as s:
                m = Milestone(
                    project_id=project_id,
                    name=m_name.strip(),
                    target_date=(m_date if isinstance(m_date, date) else None),
                )
                s.add(m)
            st.success("Milestone added")
            st.rerun()

with session_scope() as s:
    miles_rows = s.exec(
        select(Milestone)
        .where(Milestone.project_id == project_id)
        .order_by(Milestone.created_at.desc())
    ).all()

miles = [
    {
        "ID": m.id,
        "Name": m.name,
        "Target date": m.target_date.isoformat() if getattr(m, "target_date", None) else "",
        "Created": m.created_at.isoformat() if m.created_at else "",
    }
    for m in miles_rows
]

if not miles:
    st.info("No milestones yet. Add one above.")
else:
    st.dataframe(miles, use_container_width=True, hide_index=True)
