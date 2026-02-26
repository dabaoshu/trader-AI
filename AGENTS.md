# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

CChanTrader-AI is a Chinese A-share stock market intelligent trading management platform built with Python/Flask. It analyzes stocks using technical indicators and auction data, provides a web dashboard, and sends email reports.

### Running the application

```bash
# From the project root
python3 backend/app.py
# App serves on http://localhost:8080
```

See `README.md` for alternative startup methods (`run.py`, `run.sh`).

### Key details

- **No formal test framework or linter is configured.** Test files in `backend/test_*.py` are standalone scripts (not pytest/unittest). They import from legacy module names (e.g., `web_app`) and may not all run without modification.
- **No Node.js/npm required.** The frontend is server-rendered via Flask/Jinja2 templates.
- **SQLite database** (`data/cchan_web.db`) is auto-created on first app start. No external DB server needed.
- **The `/api/run_analysis` endpoint is slow** (~60s+) because it connects to external Chinese stock data APIs (BaoStock/AKShare). The app gracefully degrades to simulated data if APIs are unreachable.
- **Email features require `.env` configuration** with `SENDER_EMAIL`, `SENDER_PASSWORD`, `RECIPIENT_EMAILS`, `EMAIL_PROVIDER`. These are optional for basic development.
- **`PYTHONPATH`** must include the project root for module imports to work. Running `python3 backend/app.py` from the workspace root handles this via `sys.path.append` in the source code.
