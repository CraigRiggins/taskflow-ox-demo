"""
Database connection management.

Boundary file — imported by routes, services, and models.
Uses SQLite for simplicity; swap for Postgres in production.
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", "taskflow.db")

_connection: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    """
    Returns the global database connection.
    Creates one if it doesn't exist yet.

    Note: this is a module-level singleton — works fine for SQLite
    but is not thread-safe. A connection pool would be needed for
    a production database.
    """
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        _connection.row_factory = sqlite3.Row
    return _connection


def init_db():
    """Creates tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT    UNIQUE NOT NULL,
            name        TEXT    NOT NULL,
            password    TEXT    NOT NULL,
            role        TEXT    NOT NULL DEFAULT 'user',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT    NOT NULL,
            description  TEXT,
            status       TEXT    NOT NULL DEFAULT 'todo',
            priority     TEXT    NOT NULL DEFAULT 'medium',
            owner_id     INTEGER NOT NULL REFERENCES users(id),
            assignee_id  INTEGER REFERENCES users(id),
            due_date     TEXT,
            tags         TEXT    DEFAULT '',
            created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS comments (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id    INTEGER NOT NULL REFERENCES tasks(id),
            user_id    INTEGER NOT NULL REFERENCES users(id),
            body       TEXT    NOT NULL,
            created_at TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            action     TEXT NOT NULL,
            table_name TEXT NOT NULL,
            record_id  INTEGER,
            details    TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()


def close():
    """Closes the database connection."""
    global _connection
    if _connection:
        _connection.close()
        _connection = None
