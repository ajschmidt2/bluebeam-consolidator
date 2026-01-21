# src/llm.py
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import streamlit as st
from openai import OpenAI


@dataclass
class TriageResult:
    track: bool
    tag: str          # RFI / DECISION / COORD / CODE / COST / SCHED / QA / OTHER
    risk: str         # LOW / MED / HIGH
    required_response: str


def _get_client() -> OpenAI:
    # Prefer Streamlit secrets; fall back to env var
    api_key = None
    if hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    api_key = api_key or os.environ.get("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY. Add it to Streamlit Secrets.")

    return OpenAI(api_key=api_key)


def _get_model() -> str:
    if hasattr(st, "secrets") and "OPENAI_MODEL" in st.secrets:
        return st.secrets["OPENAI_MODEL"]
    return os.environ.get("OPENAI_MODEL", "gpt-5.2")


@st.cache_data(show_spinner=False)
def triage_comment_cached(
    comment_text: str,
    sheet: str,
    discipline: str,
    milestone: str,
) -> Dict[str, Any]:
    """
    Cached so the same comment doesn't cost you twice.
    Cache key is based on function args.
    """
    client = _get_client()
    model = _get_model()

    # Keep prompts tight to keep cost down
    instructions = (
        "You help a real estate development manager triage drawing review comments. "
        "Return ONLY valid JSON matching the schema. Be concise."
    )

    # Ask for a strict JSON object
    schema = {
        "type": "object",
        "properties": {
            "track": {"type": "boolean"},
            "tag": {
                "type": "string",
                "enum": ["RFI", "DECISION", "COORD", "CODE", "COST", "SCHED", "QA", "OTHER"],
            },
            "risk": {"type": "string", "enum": ["LOW", "MED", "HIGH"]},
            "required_response": {"type": "string"},
        },
        "required": ["track", "tag", "risk", "required_response"],
        "additionalProperties": False,
    }

    input_text = (
        f"Discipline: {discipline}\n"
        f"Sheet: {sheet}\n"
        f"Milestone: {milestone}\n"
        f"Comment: {comment_text}\n"
        "\nDecide whether to TRACK this, assign a TAG + RISK, and rewrite a clear REQUIRED RESPONSE."
    )

    # Responses API is the recommended interface for new projects. :contentReference[oaicite:3]{index=3}
    resp = client.responses.create(
        model=model,
        instructions=instructions,
        input=input_text,
        # "Structured Outputs" style: require JSON. If your SDK/model doesn’t support
        # this exact parameter, we can fall back to JSON-only prompting.
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "triage_result", "schema": schema},
        },
    )

    # The SDK provides output_text for the combined text output. :contentReference[oaicite:4]{index=4}
    raw = resp.output_text.strip()
    return json.loads(raw)
