"""Tests for authentication."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    import hashlib
    hashed = hashlib.sha256("Password1".encode()).hexdigest()
    user = {
        "id": 1, "email": "alice@example.com", "name": "Alice",
        "role": "user", "password": hashed,
        "created_at": "2026-01-01", "updated_at": "2026-01-01",
    }
    monkeypatch.setattr("app.db.queries.get_user_by_email",
                        lambda e: user if e == "alice@example.com" else None)
    monkeypatch.setattr("app.db.queries.get_user_by_id",
                        lambda i: user if i == 1 else None)
    monkeypatch.setattr("app.db.connection.init_db", lambda: None)


class TestLogin:
    def test_valid_credentials_return_token(self):
        resp = client.post("/auth/login", json={
            "email": "alice@example.com", "password": "Password1"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user_id"] == 1

    def test_wrong_password_returns_401(self):
        resp = client.post("/auth/login", json={
            "email": "alice@example.com", "password": "wrongpassword"
        })
        assert resp.status_code == 401

    def test_unknown_email_returns_401(self):
        resp = client.post("/auth/login", json={
            "email": "nobody@example.com", "password": "Password1"
        })
        assert resp.status_code == 401


class TestMe:
    def test_returns_current_user(self):
        login = client.post("/auth/login", json={
            "email": "alice@example.com", "password": "Password1"
        })
        token = login.json()["access_token"]
        resp  = client.get("/auth/me",
                           headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["email"] == "alice@example.com"
        assert "password" not in resp.json()

    def test_missing_token_returns_401(self):
        resp = client.get("/auth/me")
        assert resp.status_code == 401
