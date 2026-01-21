from __future__ import annotations

from datetime import datetime
from typing import List

import pandas as pd

from .models import CommentItem


def comments_to_dataframe(items: List[CommentItem]) -> pd.DataFrame:
    rows = []
    for it in items:
        rows.append(
            {
                "ID": it.id,
                "Project ID": it.project_id,
                "Milestone ID": it.milestone_id,
                "Discipline": it.discipline,
                "Sheet": it.sheet,
                "Subject": it.subject or "",
                "Author": it.author or "",
                "Created At": it.created_at.isoformat() if it.created_at else "",
                "Status": it.status,
                "Owner": it.owner or "",
                "Due Date": it.due_date.isoformat() if it.due_date else "",
                "Tags": it.tags or "",
                "Tracked": it.tracked,
                "Comment": it.comment_text,
                "Required Response": it.required_response or "",
            }
        )
    return pd.DataFrame(rows)


def build_consultant_package(items: List[CommentItem], header: str = "") -> str:
    # Email/Teams friendly.
    lines = []
    if header:
        lines.append(header.strip())
        lines.append("")

    if not items:
        return "(No items match your filters.)"

    # Group by sheet for readability
    items_sorted = sorted(items, key=lambda x: (x.sheet or "", x.id or 0))
    current_sheet = None
    idx = 1

    for it in items_sorted:
        if it.sheet != current_sheet:
            current_sheet = it.sheet
            lines.append(f"Sheet: {current_sheet}")

        req = (it.required_response or "").strip()
        req_line = f"Required response: {req}" if req else "Required response: (please respond with proposed resolution)"

        meta = []
        if it.subject:
            meta.append(it.subject)
        if it.author:
            meta.append(f"Reviewer: {it.author}")
        if it.due_date:
            meta.append(f"Due: {it.due_date.isoformat()}")
        if it.tags:
            meta.append(f"Tags: {it.tags}")
        meta_str = " | ".join(meta)

        lines.append(f"  {idx}. {it.comment_text}")
        if meta_str:
            lines.append(f"     ({meta_str})")
        lines.append(f"     {req_line}")
        lines.append("")
        idx += 1

    lines.append(f"Generated: {datetime.utcnow().isoformat()}Z")
    return "\n".join(lines)
