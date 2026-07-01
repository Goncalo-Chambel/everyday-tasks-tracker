# everyday-tasks-tracker

A simple local everyday task tracker: FastAPI + SQLite backend, vanilla HTML/CSS/JS dark-themed frontend.
Tasks are grouped into columns by category (add/remove columns freely) and only have two states: done or not done.

## Run locally

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv run everyday-tasks-tracker
```

Then open http://127.0.0.1:8000 in your browser.

Data is stored in `tasks.db` (SQLite) in the project root and persists across restarts.
