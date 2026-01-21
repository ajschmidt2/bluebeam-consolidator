# src/llm.py
from __future__ import annotations

import json
import re
from typing import Dict, Any

import streamlit as st

# IMPORTANT:
# This implementation uses Chat Completions for maximum compatibility
# with OpenAI python versions commonly used on Streamlit Cloud.
from openai import OpenAI


def _normalize_risk(r: str) -> str:
    r = (r or "").strip().upper()
    if r in {"LOW", "MED", "MEDIUM", "HIGH"}:
        return "MED" if r == "MEDIUM" else r
    return ""


def _normalize_tag(t: str) -> str:
    t = (t or "").strip().upper()
    # Keep it simple but consistent
    allowed = {
        "RFI", "COORD", "CODE", "SCOPE", "COST", "SCHEDULE",
        "CLASH", "SITE", "MEP", "ARCH", "STRUCT", "CIVIL",
        "QAQC", "SUBMITTAL", "OWNER", "OTHER"
    }
    return t if t in allowed else "OTHER"


def _safe_json_from_text(text: str) -> Dict[str, Any]:
    """
    Extract the first JSON object from a model response.
    """
    if not text:
        return {}
    # Try direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try to extract a JSON object from mixed text
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}


@st.cache_data(show_spinner=False)
def triage_comment_cached(
    comment_text: str,
    discipline: str = "",
    sheet: str = "",
    subject: str = "",
    milestone: str = "",
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """
    Returns a dict with:
      - tag: short category (RFI/COORD/CODE/etc.)
      - risk: LOW/MED/HIGH
      - required_response: one sentence describing the ask
      - owner: suggested owner role
      - status: suggested status (Open by default)

    Safe defaults if API key missing.
    """

    api_key = st.secrets.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        # No AI if no key
        return {
            "tag": "",
            "risk": "",
            "required_response": "",
            "owner": "",
            "status": "Open",
        }

    client = OpenAI(api_key=api_key)

    system = (
        "You are a construction/design review assistant. "
        "You triage review comments into concise structured metadata. "
        "Return ONLY valid JSON with keys: tag, risk, required_response, owner, status."
    )

    user = {
        "discipline": discipline or "",
        "sheet": sheet or "",
        "subject": subject or "",
        "milestone": milestone or "",
        "comment_text": comment_text or "",
        "instructions": (
            "tag should be one of: RFI, COORD, CODE, SCOPE, COST, SCHEDULE, CLASH, QAQC, SUBMITTAL, OWNER, OTHER. "
            "risk must be LOW, MED, or HIGH. "
            "required_response must be a single sentence describing what must be done/answered. "
            "owner should be a role like Architect, Civil, Structural, MEP, Owner, GC, Consultant. "
            "status should be Open unless clearly resolved."
        ),
    }

    # Chat Completions call (compatible)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user)},
        ],
        temperature=0.2,
    )

    text = resp.choices[0].message.content if resp and resp.choices else ""
    data = _safe_json_from_text(text)

    tag = _normalize_tag(data.get("tag", ""))
    risk = _normalize_risk(data.get("risk", ""))
    required_response = (data.get("required_response") or "").strip()
    owner = (data.get("owner") or "").strip()
    status = (data.get("status") or "Open").strip() or "Open"

    return {
        "tag": tag,
        "risk": risk,
        "required_response": required_response,
        "owner": owner,
        "status": status,
    }
