import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tasks.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    start_date TEXT NOT NULL,
    end_date TEXT,
    done INTEGER NOT NULL DEFAULT 0
);
"""


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


DEFAULT_CATEGORIES = ["Work", "Personal", "Health", "Home"]


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(SCHEMA)
        (count,) = connection.execute("SELECT COUNT(*) FROM categories").fetchone()
        if count == 0:
            connection.executemany(
                "INSERT INTO categories (name) VALUES (?)",
                [(name,) for name in DEFAULT_CATEGORIES],
            )
