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

with st.expander("➕ Create a project", expanded=True):
    c1, c2, c3 = st.columns([2,2,2])
    name = c1.text_input("Project name")
    client = c2.text_input("Client (optional)")
    location = c3.text_input("Location (optional)")
    if st.button("Create project", type="primary"):
        if not name.strip():
            st.error("Project name is required")
        else:
            with session_scope() as s:
                p = Project(name=name.strip(), client=client.strip() or None, location=location.strip() or None)
                s.add(p)
                s.commit()
            st.success("Project created")
            st.rerun()

with session_scope() as s:
    projects = s.exec(select(Project).order_by(Project.is_active.desc(), Project.name)).all()

if not projects:
    st.warning("Create your first project above.")
    st.stop()

project_opts = {f"{p.name} (#{p.id})": p.id for p in projects}
selected_label = st.selectbox("Select project", list(project_opts.keys()))
project_id = project_opts[selected_label]

with session_scope() as s:
    proj = s.get(Project, project_id)

st.subheader("Project details")
colA, colB, colC = st.columns([2,2,1])
colA.write(f"**Name:** {proj.name}")
colB.write(f"**Client:** {proj.client or '—'}")
colC.write(f"**Active:** {proj.is_active}")

if st.button("Toggle Active / Archived"):
    with session_scope() as s:
        p = s.get(Project, project_id)
        p.is_active = not p.is_active
        s.add(p)
        s.commit()
    st.rerun()

st.divider()

st.subheader("Milestones")
with st.expander("➕ Add milestone", expanded=False):
    m_name = st.text_input("Milestone name (e.g., 100% DD Review)")
    m_date = st.date_input("Target date (optional)", value=None)
    if st.button("Add milestone"):
        if not m_name.strip():
            st.error("Milestone name is required")
        else:
            with session_scope() as s:
                m = Milestone(project_id=project_id, name=m_name.strip(), target_date=m_date if isinstance(m_date, date) else None)
                s.add(m)
                s.commit()
            st.success("Milestone added")
            st.rerun()

with session_scope() as s:
    miles = s.exec(select(Milestone).where(Milestone.project_id == project_id).order_by(Milestone.created_at.desc())).all()

if not miles:
    st.info("No milestones yet. Add one above.")
else:
    st.dataframe(
        [
            {"ID": m.id, "Name": m.name, "Target date": m.target_date.isoformat() if m.target_date else "", "Created": m.created_at.isoformat()} 
            for m in miles
        ],
        use_container_width=True,
        hide_index=True,
    )
