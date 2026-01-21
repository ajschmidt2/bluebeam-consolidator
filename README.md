# Bluebeam Review Comment Consolidator (Streamlit)

A lightweight, single-user web app to import **Bluebeam Markups Summary (CSV)** exports, consolidate review comments, triage/assign them, and generate **consultant response packages**.

This is designed to **complement** Bluebeam (where markups happen) by centralizing outcomes (status, owner, required response, tracked/untracked).

## Features (MVP)
- Projects + milestones
- Import Bluebeam Markups Summary **CSV**
  - column mapping UI
  - dedupe via stable hash fingerprint
- Dashboard filters (discipline/sheet/author/status/tracked + text search)
- Bulk updates (status/owner/due date/tags/tracked)
- Consultant response package builder + exports (TXT + CSV)

## Security ("just me")
Use **both** of these:
1) **Streamlit Community Cloud app visibility = Private**
2) App-level password gate via **APP_PASSWORD** stored in Streamlit **Secrets**

> This gives you platform authentication + your own password gate.

## Quick Start (local)
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Local environment variables
Create a `.env` file (optional):
```env
APP_PASSWORD=choose-a-strong-password
DATABASE_URL=sqlite:///./data/app.db
```

Then run:
```bash
streamlit run app.py
```

## Deploy to Streamlit Community Cloud
1) Push this repo to GitHub.
2) In Streamlit Cloud, create a new app from this repo and set it to **Private**.
3) Add Secrets (App Settings → Secrets):

```toml
APP_PASSWORD="your-strong-password"
# Recommended for persistence / multi-device reliability:
# DATABASE_URL="postgresql+psycopg://..."
```

### Notes on persistence
- The MVP uses SQLite by default: `sqlite:///./data/app.db`.
- For best persistence (and future multi-user), use Postgres (e.g., Supabase). Set `DATABASE_URL` accordingly.

## Bluebeam Export Guidance
In Bluebeam Revu:
1) Open **Markups List**
2) Filter to the relevant set/reviewers if desired
3) **Summary** → export to **CSV**
4) Import into this app (Import page)

## Recommended workflow
1) Mark up in Bluebeam as usual.
2) Export Markups Summary CSV.
3) Import CSV into this app under the correct Project + Milestone.
4) Triage: set **Tracked** on the items you want to manage.
5) Assign Owner / Due Date / Required Response.
6) Generate consultant response package for items with Status = **Needs Response**.
7) Verify changes in next set before closing.

## Optional AI add-ons (later)
This repo is structured to add optional AI helpers (ChatGPT) later:
- Auto-tag: RFI / DECISION / COORD / CODE / COST / SCHED
- Track vs Ignore recommendation
- Required response rewriter
- Consultant package drafting

Keep AI suggestions **opt-in** (button click) to control cost and maintain accountability.

## Repository layout
```
.
├── app.py
├── pages/
│   ├── 1_Projects.py
│   ├── 2_Import_Bluebeam_CSV.py
│   ├── 3_Comments_Dashboard.py
│   └── 4_Consultant_Package.py
├── src/
│   ├── auth.py
│   ├── db.py
│   ├── exporters.py
│   ├── import_bluebeam.py
│   ├── models.py
│   └── settings.py
├── requirements.txt
└── .streamlit/config.toml
```

## License
Private / personal use.
