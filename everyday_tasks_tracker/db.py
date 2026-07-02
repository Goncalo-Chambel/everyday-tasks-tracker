import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tasks.db"

DEFAULT_COLOR = "#6c8cff"

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL DEFAULT '#6c8cff',
    position INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    start_date TEXT NOT NULL,
    end_date TEXT,
    done INTEGER NOT NULL DEFAULT 0,
    completed_date TEXT
);
"""

COLOR_PALETTE = [
    "#6c8cff",
    "#5cc98c",
    "#e5677a",
    "#f0b429",
    "#a78bfa",
    "#4fd1c5",
    "#f472b6",
    "#fb923c",
]


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


DEFAULT_CATEGORIES = [
    ("Work", COLOR_PALETTE[0]),
    ("Personal", COLOR_PALETTE[1]),
    ("Health", COLOR_PALETTE[2]),
    ("Home", COLOR_PALETTE[3]),
]


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(SCHEMA)

        columns = {row["name"] for row in connection.execute("PRAGMA table_info(categories)")}
        if "color" not in columns:
            connection.execute(f"ALTER TABLE categories ADD COLUMN color TEXT NOT NULL DEFAULT '{DEFAULT_COLOR}'")
            for row in connection.execute("SELECT id FROM categories").fetchall():
                color = COLOR_PALETTE[row["id"] % len(COLOR_PALETTE)]
                connection.execute("UPDATE categories SET color = ? WHERE id = ?", (color, row["id"]))
        if "position" not in columns:
            connection.execute("ALTER TABLE categories ADD COLUMN position INTEGER NOT NULL DEFAULT 0")
            rows = connection.execute("SELECT id FROM categories ORDER BY name").fetchall()
            for position, row in enumerate(rows):
                connection.execute("UPDATE categories SET position = ? WHERE id = ?", (position, row["id"]))

        task_columns = {row["name"] for row in connection.execute("PRAGMA table_info(tasks)")}
        if "completed_date" not in task_columns:
            connection.execute("ALTER TABLE tasks ADD COLUMN completed_date TEXT")
            connection.execute(
                "UPDATE tasks SET completed_date = ? WHERE done = 1", (date.today().isoformat(),)
            )

        (count,) = connection.execute("SELECT COUNT(*) FROM categories").fetchone()
        if count == 0:
            connection.executemany(
                "INSERT INTO categories (name, color, position) VALUES (?, ?, ?)",
                [(name, color, position) for position, (name, color) in enumerate(DEFAULT_CATEGORIES)],
            )
