# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- Install dependencies: `uv sync`
- Run the app: `uv run everyday-tasks-tracker` (serves on http://127.0.0.1:1234, backed by `tasks.db` in the project root)
- Format: `uv run black .`
- Lint: `uv run ruff check .`

There is no test suite in this repository.

## Architecture

FastAPI + SQLite backend (`everyday_tasks_tracker/`) serving a vanilla HTML/CSS/JS frontend (`everyday_tasks_tracker/static/`) with no build step — `app.js` is loaded directly by the browser and talks to the backend purely via `fetch` calls against the JSON API.

- `main.py` — the FastAPI app and all HTTP routes (`/api/categories`, `/api/tasks`), plus serving `index.html` at `/` and mounting `/static`.
- `db.py` — raw `sqlite3` access via a `get_connection()` context manager (commits on success, no ORM). `init_db()` runs on startup through the `lifespan` hook in `main.py`; it both creates the schema and applies lightweight migrations by checking `PRAGMA table_info` and issuing `ALTER TABLE` for any column that's missing. There's no migration framework, so schema changes must extend this same pattern.
- `models.py` — Pydantic request/response schemas shared by the routes.
- `tasks.db` — SQLite file at the project root (gitignored); the sole source of truth, persists across restarts.

### Task data model

Tasks belong to a category and only ever have two states, done or not done (`done` boolean), plus three separate date fields that are easy to conflate:
- `start_date` — set once at creation.
- `end_date` — an optional user-set due date, unrelated to completion.
- `completed_date` — set to today's date whenever `done` is flipped to `true` via `PATCH /api/tasks/{id}`, and cleared when flipped back to `false`.

`GET /api/tasks` has non-obvious `done` filter semantics: passing `done=true`/`done=false` filters exactly on that boolean, but when `done` is omitted (the frontend's default request), the query instead returns tasks that are either not done, or done with `completed_date` equal to today. This means completed tasks silently drop out of the default view once the day they were completed has passed, while every not-done task always stays visible regardless of date.

### Categories

Categories have a `position` column controlling column order on the board, updated in bulk via `PUT /api/categories/reorder` after drag-and-drop reordering in `app.js`, and a `color` picked from a fixed palette (`COLOR_PALETTE` in `db.py`, mirrored as `CATEGORY_COLORS` in `app.js`).
