"""
Database query helpers.

These started as simple one-liners and grew over time as requirements
were added. Several functions now do more than their name suggests.
"""

from app.db.connection import get_connection


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_connection()
    row  = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return dict(row) if row else None


def get_user_by_email(email: str) -> dict | None:
    conn = get_connection()
    row  = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()
    return dict(row) if row else None


def get_all_users() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def create_user(email: str, name: str, password: str, role: str = "user") -> int:
    conn = get_connection()
    cur  = conn.execute(
        "INSERT INTO users (email, name, password, role) VALUES (?, ?, ?, ?)",
        (email, name, password, role),
    )
    conn.commit()
    return cur.lastrowid


def update_user(user_id: int, **kwargs) -> bool:
    if not kwargs:
        return False
    conn    = get_connection()
    fields  = ", ".join(f"{k} = ?" for k in kwargs)
    values  = list(kwargs.values()) + [user_id]
    conn.execute(
        f"UPDATE users SET {fields}, updated_at = datetime('now') WHERE id = ?",
        values,
    )
    conn.commit()
    return True


def delete_user(user_id: int) -> bool:
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    return True


def get_task_by_id(task_id: int) -> dict | None:
    conn = get_connection()
    row  = conn.execute(
        "SELECT * FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    return dict(row) if row else None


def get_tasks_for_user(
    user_id:  int,
    status:   str | None = None,
    priority: str | None = None,
    tag:      str | None = None,
) -> list[dict]:
    """
    Fetches tasks for a user with optional filters.
    Builds the WHERE clause by string concatenation — works but
    is harder to maintain as filter options grow.
    """
    conn  = get_connection()
    query = "SELECT * FROM tasks WHERE owner_id = ? OR assignee_id = ?"
    args: list = [user_id, user_id]

    if status:
        query += " AND status = ?"
        args.append(status)
    if priority:
        query += " AND priority = ?"
        args.append(priority)
    if tag:
        query += " AND tags LIKE ?"
        args.append(f"%{tag}%")

    query += " ORDER BY created_at DESC"

    rows = conn.execute(query, args).fetchall()
    return [dict(r) for r in rows]


def create_task(
    title:       str,
    owner_id:    int,
    description: str = "",
    status:      str = "todo",
    priority:    str = "medium",
    assignee_id: int | None = None,
    due_date:    str | None = None,
    tags:        str = "",
) -> int:
    conn = get_connection()
    cur  = conn.execute(
        """INSERT INTO tasks
           (title, description, status, priority, owner_id, assignee_id, due_date, tags)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (title, description, status, priority, owner_id, assignee_id, due_date, tags),
    )
    conn.commit()
    return cur.lastrowid


def update_task(task_id: int, **kwargs) -> bool:
    if not kwargs:
        return False
    conn   = get_connection()
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [task_id]
    conn.execute(
        f"UPDATE tasks SET {fields}, updated_at = datetime('now') WHERE id = ?",
        values,
    )
    conn.commit()
    return True


def delete_task(task_id: int) -> bool:
    conn = get_connection()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    return True


def get_comments_for_task(task_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT c.*, u.name as author_name, u.email as author_email
           FROM comments c
           JOIN users u ON c.user_id = u.id
           WHERE c.task_id = ?
           ORDER BY c.created_at ASC""",
        (task_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def add_comment(task_id: int, user_id: int, body: str) -> int:
    conn = get_connection()
    cur  = conn.execute(
        "INSERT INTO comments (task_id, user_id, body) VALUES (?, ?, ?)",
        (task_id, user_id, body),
    )
    conn.commit()
    return cur.lastrowid


def log_audit(
    action:     str,
    table_name: str,
    record_id:  int | None = None,
    user_id:    int | None = None,
    details:    str | None = None,
):
    conn = get_connection()
    conn.execute(
        "INSERT INTO audit_log (user_id, action, table_name, record_id, details) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, action, table_name, record_id, details),
    )
    conn.commit()
