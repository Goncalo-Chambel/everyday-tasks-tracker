import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from daily_tasks_tracker.db import get_connection, init_db
from daily_tasks_tracker.models import CategoryCreate, CategoryOut, TaskCreate, TaskOut, TaskUpdate

STATIC_DIR = Path(__file__).resolve().parent / "static"

TASK_SELECT = """
    SELECT tasks.*, categories.name AS category_name
    FROM tasks
    JOIN categories ON categories.id = tasks.category_id
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="Daily Tasks Tracker", lifespan=lifespan)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _row_to_task(row: sqlite3.Row) -> TaskOut:
    return TaskOut(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        category_id=row["category_id"],
        category_name=row["category_name"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        done=bool(row["done"]),
    )


@app.get("/api/categories", response_model=list[CategoryOut])
def list_categories() -> list[CategoryOut]:
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM categories ORDER BY name").fetchall()
    return [CategoryOut(id=row["id"], name=row["name"]) for row in rows]


@app.post("/api/categories", response_model=CategoryOut, status_code=201)
def create_category(payload: CategoryCreate) -> CategoryOut:
    name = payload.name.strip()
    with get_connection() as connection:
        existing = connection.execute("SELECT * FROM categories WHERE name = ?", (name,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Category already exists")
        cursor = connection.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        category_id = cursor.lastrowid
    return CategoryOut(id=category_id, name=name)


@app.delete("/api/categories/{category_id}", status_code=204)
def delete_category(category_id: int) -> None:
    with get_connection() as connection:
        category = connection.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        (task_count,) = connection.execute(
            "SELECT COUNT(*) FROM tasks WHERE category_id = ?", (category_id,)
        ).fetchone()
        if task_count > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Category still has {task_count} task(s). Delete or move them first.",
            )
        connection.execute("DELETE FROM categories WHERE id = ?", (category_id,))


@app.get("/api/tasks", response_model=list[TaskOut])
def list_tasks(done: bool | None = None, category_id: int | None = None) -> list[TaskOut]:
    query = TASK_SELECT
    conditions = []
    params: list[object] = []
    if done is not None:
        conditions.append("tasks.done = ?")
        params.append(int(done))
    if category_id is not None:
        conditions.append("tasks.category_id = ?")
        params.append(category_id)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY tasks.done, tasks.start_date DESC, tasks.id DESC"
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [_row_to_task(row) for row in rows]


@app.post("/api/tasks", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate) -> TaskOut:
    with get_connection() as connection:
        category = connection.execute("SELECT * FROM categories WHERE id = ?", (payload.category_id,)).fetchone()
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        cursor = connection.execute(
            """
            INSERT INTO tasks (title, description, category_id, start_date, end_date, done)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (
                payload.title.strip(),
                payload.description.strip() if payload.description else None,
                payload.category_id,
                date.today().isoformat(),
                payload.end_date.isoformat() if payload.end_date else None,
            ),
        )
        task_id = cursor.lastrowid
        row = connection.execute(TASK_SELECT + " WHERE tasks.id = ?", (task_id,)).fetchone()
    return _row_to_task(row)


@app.patch("/api/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate) -> TaskOut:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    with get_connection() as connection:
        existing = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Task not found")

        if "category_id" in updates:
            category = connection.execute("SELECT * FROM categories WHERE id = ?", (updates["category_id"],)).fetchone()
            if category is None:
                raise HTTPException(status_code=404, detail="Category not found")

        columns = []
        params: list[object] = []
        for field, value in updates.items():
            if field == "done":
                value = int(value)
            elif field == "end_date" and value is not None:
                value = value.isoformat()
            elif field in ("title", "description") and isinstance(value, str):
                value = value.strip()
            columns.append(f"{field} = ?")
            params.append(value)
        params.append(task_id)
        connection.execute(f"UPDATE tasks SET {', '.join(columns)} WHERE id = ?", params)

        row = connection.execute(TASK_SELECT + " WHERE tasks.id = ?", (task_id,)).fetchone()
    return _row_to_task(row)


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int) -> None:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")


def run() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    run()
