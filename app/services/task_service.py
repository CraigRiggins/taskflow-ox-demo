"""
Task service — business logic for task management.

This module started as a few helper functions and grew organically
as requirements were added. Several functions handle more than one
concern and the validation logic has been duplicated across methods
rather than extracted into shared helpers.

This is the primary hotspot in the codebase — high churn, high complexity.
"""

import re
import json
from datetime import datetime, date

from app.db import queries
from app.db.connection import get_connection


VALID_STATUSES   = {"todo", "in_progress", "review", "done", "cancelled"}
VALID_PRIORITIES = {"low", "medium", "high", "urgent"}


def create_task(
    title:       str,
    owner_id:    int,
    description: str = "",
    status:      str = "todo",
    priority:    str = "medium",
    assignee_id: int | None = None,
    due_date:    str | None = None,
    tags:        str = "",
) -> dict:
    """
    Creates a new task after validating all fields.

    Validation, business logic, audit logging, and notification
    triggering are all handled in this single function — a sign
    this should be broken into smaller, focused functions.
    """
    # --- validate title ---
    if not title or not title.strip():
        raise ValueError("Title cannot be empty")
    if len(title.strip()) > 200:
        raise ValueError("Title too long (max 200 chars)")
    title = title.strip()

    # --- validate status ---
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(VALID_STATUSES)}")

    # --- validate priority ---
    if priority not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority '{priority}'. Must be one of: {', '.join(VALID_PRIORITIES)}")

    # --- validate due_date ---
    if due_date:
        try:
            parsed = datetime.strptime(due_date, "%Y-%m-%d").date()
            if parsed < date.today():
                raise ValueError("Due date cannot be in the past")
        except ValueError as e:
            if "does not match format" in str(e):
                raise ValueError("Due date must be in YYYY-MM-DD format")
            raise

    # --- validate assignee exists if provided ---
    if assignee_id is not None:
        assignee = queries.get_user_by_id(assignee_id)
        if not assignee:
            raise ValueError(f"Assignee {assignee_id} does not exist")

    # --- validate owner exists ---
    owner = queries.get_user_by_id(owner_id)
    if not owner:
        raise ValueError(f"Owner {owner_id} does not exist")

    # --- validate tags ---
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        for tag in tag_list:
            if len(tag) > 50:
                raise ValueError(f"Tag '{tag}' exceeds max length of 50 chars")
            if not re.match(r"^[a-zA-Z0-9_\-]+$", tag):
                raise ValueError(f"Tag '{tag}' contains invalid characters. Use letters, numbers, hyphens, underscores.")
        tags = ",".join(tag_list)

    task_id = queries.create_task(
        title=title,
        owner_id=owner_id,
        description=description or "",
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        due_date=due_date,
        tags=tags,
    )

    queries.log_audit(
        action="create",
        table_name="tasks",
        record_id=task_id,
        user_id=owner_id,
        details=json.dumps({"title": title, "status": status, "priority": priority}),
    )

    _maybe_notify_assignee(assignee_id, task_id, title, "assigned")

    task = queries.get_task_by_id(task_id)
    return task


def update_task(
    task_id:     int,
    user_id:     int,
    title:       str | None = None,
    description: str | None = None,
    status:      str | None = None,
    priority:    str | None = None,
    assignee_id: int | None = None,
    due_date:    str | None = None,
    tags:        str | None = None,
) -> dict:
    """
    Updates a task. Checks ownership/admin, validates each field,
    detects status transitions, and fires notifications.

    This function has grown to 100+ lines and handles too many concerns.
    The status transition logic, permission check, and notification
    firing should each be separate functions.
    """
    task = queries.get_task_by_id(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")

    # permission check — owner or admin
    user = queries.get_user_by_id(user_id)
    if not user:
        raise ValueError("User not found")
    if task["owner_id"] != user_id and user["role"] != "admin":
        raise PermissionError("Only the task owner or an admin can update this task")

    updates: dict = {}

    if title is not None:
        if not title.strip():
            raise ValueError("Title cannot be empty")
        if len(title.strip()) > 200:
            raise ValueError("Title too long (max 200 chars)")
        updates["title"] = title.strip()

    if description is not None:
        updates["description"] = description

    if status is not None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'")
        # detect transition to done — record completion time
        if status == "done" and task["status"] != "done":
            updates["updated_at"] = datetime.utcnow().isoformat()
        updates["status"] = status

    if priority is not None:
        if priority not in VALID_PRIORITIES:
            raise ValueError(f"Invalid priority '{priority}'")
        updates["priority"] = priority

    if assignee_id is not None:
        assignee = queries.get_user_by_id(assignee_id)
        if not assignee:
            raise ValueError(f"Assignee {assignee_id} does not exist")
        updates["assignee_id"] = assignee_id

    if due_date is not None:
        if due_date == "":
            updates["due_date"] = None
        else:
            try:
                parsed = datetime.strptime(due_date, "%Y-%m-%d").date()
                if parsed < date.today():
                    raise ValueError("Due date cannot be in the past")
                updates["due_date"] = due_date
            except ValueError as e:
                if "does not match format" in str(e):
                    raise ValueError("Due date must be in YYYY-MM-DD format")
                raise

    if tags is not None:
        if tags == "":
            updates["tags"] = ""
        else:
            tag_list = [t.strip() for t in tags.split(",")]
            for tag in tag_list:
                if len(tag) > 50:
                    raise ValueError(f"Tag '{tag}' exceeds max length of 50 chars")
                if not re.match(r"^[a-zA-Z0-9_\-]+$", tag):
                    raise ValueError(f"Tag '{tag}' contains invalid characters")
            updates["tags"] = ",".join(tag_list)

    if not updates:
        return task

    queries.update_task(task_id, **updates)
    queries.log_audit(
        action="update",
        table_name="tasks",
        record_id=task_id,
        user_id=user_id,
        details=json.dumps({k: str(v) for k, v in updates.items()}),
    )

    # notify assignee if assignment changed
    new_assignee = updates.get("assignee_id")
    if new_assignee and new_assignee != task.get("assignee_id"):
        title_str = updates.get("title", task["title"])
        _maybe_notify_assignee(new_assignee, task_id, title_str, "assigned")

    # notify owner if task marked done
    if updates.get("status") == "done":
        _maybe_notify_owner(task["owner_id"], task_id, task["title"], "completed")

    return queries.get_task_by_id(task_id)


def delete_task(task_id: int, user_id: int) -> bool:
    """Deletes a task — owner or admin only."""
    task = queries.get_task_by_id(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")

    user = queries.get_user_by_id(user_id)
    if not user:
        raise ValueError("User not found")
    if task["owner_id"] != user_id and user["role"] != "admin":
        raise PermissionError("Only the task owner or an admin can delete this task")

    queries.delete_task(task_id)
    queries.log_audit(
        action="delete",
        table_name="tasks",
        record_id=task_id,
        user_id=user_id,
    )
    return True


def get_tasks(
    user_id:  int,
    status:   str | None = None,
    priority: str | None = None,
    tag:      str | None = None,
) -> list[dict]:
    """Returns tasks for a user with optional filters."""
    if status and status not in VALID_STATUSES:
        raise ValueError(f"Invalid status filter '{status}'")
    if priority and priority not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority filter '{priority}'")

    tasks = queries.get_tasks_for_user(user_id, status, priority, tag)

    # enrich each task with computed fields
    enriched = []
    for task in tasks:
        task = dict(task)
        task["is_overdue"] = _is_overdue(task)
        task["tag_list"]   = [t for t in task.get("tags", "").split(",") if t]
        enriched.append(task)

    return enriched


def add_comment(task_id: int, user_id: int, body: str) -> dict:
    """Adds a comment to a task."""
    if not body or not body.strip():
        raise ValueError("Comment body cannot be empty")
    if len(body) > 5000:
        raise ValueError("Comment too long (max 5000 chars)")

    task = queries.get_task_by_id(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")

    comment_id = queries.add_comment(task_id, user_id, body.strip())
    queries.log_audit(
        action="comment",
        table_name="tasks",
        record_id=task_id,
        user_id=user_id,
    )

    # notify task owner if commenter is not the owner
    if task["owner_id"] != user_id:
        _maybe_notify_owner(task["owner_id"], task_id, task["title"], "commented")

    comments = queries.get_comments_for_task(task_id)
    return next(c for c in comments if c["id"] == comment_id)


def get_task_stats(user_id: int) -> dict:
    """
    Returns aggregate statistics for a user's tasks.

    Fetches all tasks then counts in Python — would be more efficient
    as a GROUP BY query but this was simpler to write initially.
    """
    tasks = queries.get_tasks_for_user(user_id)

    stats: dict = {
        "total":       len(tasks),
        "by_status":   {},
        "by_priority": {},
        "overdue":     0,
    }

    for task in tasks:
        status   = task["status"]
        priority = task["priority"]

        stats["by_status"][status]     = stats["by_status"].get(status, 0) + 1
        stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1

        if _is_overdue(task):
            stats["overdue"] += 1

    return stats


def _is_overdue(task: dict) -> bool:
    """Returns True if the task is past its due date and not done."""
    if not task.get("due_date"):
        return False
    if task.get("status") in ("done", "cancelled"):
        return False
    try:
        due = datetime.strptime(task["due_date"], "%Y-%m-%d").date()
        return due < date.today()
    except (ValueError, TypeError):
        return False


def _maybe_notify_assignee(
    assignee_id: int | None,
    task_id:     int,
    task_title:  str,
    event:       str,
):
    """
    Placeholder for notification logic.
    In production this would send an email or push notification.
    Currently a no-op — the notification system hasn't been built yet.
    """
    if assignee_id is None:
        return
    # TODO: implement email notifications
    # email_service.send_task_notification(assignee_id, task_id, task_title, event)
    pass


def _maybe_notify_owner(
    owner_id:   int,
    task_id:    int,
    task_title: str,
    event:      str,
):
    """
    Placeholder for notification logic.
    Same TODO as _maybe_notify_assignee — duplicated stub.
    """
    # TODO: implement email notifications
    pass
