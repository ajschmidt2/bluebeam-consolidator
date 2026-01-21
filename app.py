import streamlit as st

from src.auth import require_login
from src.db import init_db

st.set_page_config(page_title="Bluebeam Review Consolidator", layout="wide")

init_db()
require_login()

st.title("Bluebeam Review Comment Consolidator")
st.write(
    "Use the pages in the left sidebar to manage projects, import Bluebeam Markups Summary CSVs, "
    "triage comments, and export consultant response packages."
)

st.info(
    "Tip: Keep this app private in Streamlit Cloud **and** set an APP_PASSWORD in Streamlit secrets."
)
