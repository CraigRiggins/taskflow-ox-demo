"""Tests for task service business logic."""

import pytest
from unittest.mock import patch, MagicMock

from app.services import task_service


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    """Patches all database calls so tests run without a real DB."""
    fake_user  = {"id": 1, "email": "alice@example.com",
                  "name": "Alice", "role": "user", "password": "x"}
    fake_task  = {
        "id": 1, "title": "Write tests", "description": "",
        "status": "todo", "priority": "medium",
        "owner_id": 1, "assignee_id": None,
        "due_date": None, "tags": "",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }

    monkeypatch.setattr("app.db.queries.get_user_by_id",   lambda uid: fake_user if uid == 1 else None)
    monkeypatch.setattr("app.db.queries.get_task_by_id",   lambda tid: dict(fake_task) if tid == 1 else None)
    monkeypatch.setattr("app.db.queries.create_task",      lambda **kw: 1)
    monkeypatch.setattr("app.db.queries.update_task",      lambda tid, **kw: True)
    monkeypatch.setattr("app.db.queries.delete_task",      lambda tid: True)
    monkeypatch.setattr("app.db.queries.get_tasks_for_user", lambda *a, **kw: [fake_task])
    monkeypatch.setattr("app.db.queries.add_comment",      lambda *a: 1)
    monkeypatch.setattr("app.db.queries.get_comments_for_task", lambda tid: [])
    monkeypatch.setattr("app.db.queries.log_audit",        lambda **kw: None)


class TestCreateTask:
    def test_creates_valid_task(self):
        task = task_service.create_task("Write tests", owner_id=1)
        assert task["id"] == 1

    def test_rejects_empty_title(self):
        with pytest.raises(ValueError, match="empty"):
            task_service.create_task("", owner_id=1)

    def test_rejects_title_too_long(self):
        with pytest.raises(ValueError, match="long"):
            task_service.create_task("x" * 201, owner_id=1)

    def test_rejects_invalid_status(self):
        with pytest.raises(ValueError, match="Invalid status"):
            task_service.create_task("T", owner_id=1, status="nope")

    def test_rejects_invalid_priority(self):
        with pytest.raises(ValueError, match="Invalid priority"):
            task_service.create_task("T", owner_id=1, priority="critical")

    def test_rejects_past_due_date(self):
        with pytest.raises(ValueError, match="past"):
            task_service.create_task("T", owner_id=1, due_date="2020-01-01")

    def test_rejects_invalid_tag_chars(self):
        with pytest.raises(ValueError, match="invalid characters"):
            task_service.create_task("T", owner_id=1, tags="tag with spaces")

    def test_rejects_nonexistent_owner(self, monkeypatch):
        monkeypatch.setattr("app.db.queries.get_user_by_id", lambda uid: None)
        with pytest.raises(ValueError, match="does not exist"):
            task_service.create_task("T", owner_id=999)


class TestUpdateTask:
    def test_owner_can_update(self):
        task = task_service.update_task(1, user_id=1, title="Updated title")
        assert task is not None

    def test_non_owner_cannot_update(self, monkeypatch):
        other = {"id": 2, "email": "b@b.com", "name": "B",
                 "role": "user", "password": "x"}
        monkeypatch.setattr(
            "app.db.queries.get_user_by_id",
            lambda uid: other if uid == 2 else {"id": 1, "role": "user",
                                                "name": "A", "email": "a@a.com",
                                                "password": "x"},
        )
        with pytest.raises(PermissionError):
            task_service.update_task(1, user_id=2, title="Hijacked")

    def test_admin_can_update_any_task(self, monkeypatch):
        admin = {"id": 2, "email": "admin@x.com", "name": "Admin",
                 "role": "admin", "password": "x"}
        monkeypatch.setattr(
            "app.db.queries.get_user_by_id",
            lambda uid: admin if uid == 2
            else {"id": 1, "role": "user", "name": "A",
                  "email": "a@a.com", "password": "x"},
        )
        task = task_service.update_task(1, user_id=2, status="done")
        assert task is not None

    def test_rejects_nonexistent_task(self, monkeypatch):
        monkeypatch.setattr("app.db.queries.get_task_by_id", lambda tid: None)
        with pytest.raises(ValueError, match="not found"):
            task_service.update_task(999, user_id=1, title="x")


class TestDeleteTask:
    def test_owner_can_delete(self):
        assert task_service.delete_task(1, user_id=1) is True

    def test_non_owner_cannot_delete(self, monkeypatch):
        other = {"id": 2, "email": "b@b.com", "name": "B",
                 "role": "user", "password": "x"}
        monkeypatch.setattr(
            "app.db.queries.get_user_by_id",
            lambda uid: other if uid == 2
            else {"id": 1, "role": "user", "name": "A",
                  "email": "a@a.com", "password": "x"},
        )
        with pytest.raises(PermissionError):
            task_service.delete_task(1, user_id=2)


class TestGetTasks:
    def test_returns_tasks_with_enrichment(self):
        tasks = task_service.get_tasks(user_id=1)
        assert isinstance(tasks, list)
        assert "is_overdue" in tasks[0]
        assert "tag_list"   in tasks[0]

    def test_rejects_invalid_status_filter(self):
        with pytest.raises(ValueError, match="Invalid status"):
            task_service.get_tasks(user_id=1, status="bogus")


class TestIsOverdue:
    def test_past_due_date_is_overdue(self):
        task = {"due_date": "2020-01-01", "status": "todo"}
        assert task_service._is_overdue(task) is True

    def test_done_task_not_overdue(self):
        task = {"due_date": "2020-01-01", "status": "done"}
        assert task_service._is_overdue(task) is False

    def test_no_due_date_not_overdue(self):
        task = {"due_date": None, "status": "todo"}
        assert task_service._is_overdue(task) is False
