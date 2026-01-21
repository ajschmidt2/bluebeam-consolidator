from __future__ import annotations

import hmac
import os

import streamlit as st


def _get_password() -> str:
    # Prefer Streamlit secrets; fallback to env var.
    if hasattr(st, "secrets") and "APP_PASSWORD" in st.secrets:
        return str(st.secrets["APP_PASSWORD"])
    return os.getenv("APP_PASSWORD", "")


def require_login() -> None:
    """Simple single-user password gate.

    Security notes:
    - Store APP_PASSWORD in Streamlit secrets (not in repo).
    - Use Streamlit Cloud 'Private app' in addition for best protection.
    """
    if st.session_state.get("_authed") is True:
        return

    st.sidebar.markdown("### 🔒 Login")
    pwd = st.sidebar.text_input("Password", type="password", key="_pwd")

    if st.sidebar.button("Unlock", use_container_width=True):
        expected = _get_password()
        if not expected:
            st.sidebar.error("APP_PASSWORD is not set in secrets/env.")
            st.stop()

        if hmac.compare_digest(pwd or "", expected):
            st.session_state["_authed"] = True
            st.sidebar.success("Unlocked")
        else:
            st.sidebar.error("Incorrect password")
            st.stop()

    st.stop()
