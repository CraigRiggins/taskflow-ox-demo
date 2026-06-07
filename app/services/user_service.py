"""
User service — business logic for user management.

Note: email validation and password rules are duplicated from
app/models/user.py. They evolved independently as the model
and service were written by different people at different times.
"""

import re
import hashlib
import secrets
import json

from app.db import queries


def create_user(
    email:    str,
    name:     str,
    password: str,
    role:     str = "user",
) -> dict:
    """Creates a new user after validation."""

    # email validation — duplicated from UserCreate.validate_email in models/user.py
    if not email or not email.strip():
        raise ValueError("Email cannot be empty")
    email = email.lower().strip()
    if not re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", email):
        raise ValueError("Invalid email address")

    # name validation
    if not name or not name.strip():
        raise ValueError("Name cannot be empty")
    if len(name.strip()) > 100:
        raise ValueError("Name too long (max 100 chars)")
    name = name.strip()

    # password validation — rules not enforced in the model layer
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one number")

    # role validation
    if role not in ("user", "admin", "viewer"):
        raise ValueError(f"Invalid role '{role}'")

    # check email uniqueness
    existing = queries.get_user_by_email(email)
    if existing:
        raise ValueError(f"Email '{email}' is already registered")

    hashed = _hash_password(password)
    user_id = queries.create_user(email, name, hashed, role)

    queries.log_audit(
        action="create",
        table_name="users",
        record_id=user_id,
        details=json.dumps({"email": email, "role": role}),
    )

    return queries.get_user_by_id(user_id)


def update_user(
    user_id:         int,
    requesting_user: int,
    name:            str | None = None,
    email:           str | None = None,
    role:            str | None = None,
) -> dict:
    """Updates a user — self or admin only."""
    user = queries.get_user_by_id(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    requester = queries.get_user_by_id(requesting_user)
    if not requester:
        raise ValueError("Requesting user not found")
    if user_id != requesting_user and requester["role"] != "admin":
        raise PermissionError("You can only update your own profile")

    updates: dict = {}

    if name is not None:
        if not name.strip():
            raise ValueError("Name cannot be empty")
        updates["name"] = name.strip()

    if email is not None:
        email = email.lower().strip()
        # email validation duplicated again here
        if not re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", email):
            raise ValueError("Invalid email address")
        existing = queries.get_user_by_email(email)
        if existing and existing["id"] != user_id:
            raise ValueError(f"Email '{email}' is already in use")
        updates["email"] = email

    if role is not None:
        if requester["role"] != "admin":
            raise PermissionError("Only admins can change user roles")
        if role not in ("user", "admin", "viewer"):
            raise ValueError(f"Invalid role '{role}'")
        updates["role"] = role

    if not updates:
        return user

    queries.update_user(user_id, **updates)
    queries.log_audit(
        action="update",
        table_name="users",
        record_id=user_id,
        user_id=requesting_user,
        details=json.dumps(list(updates.keys())),
    )

    return queries.get_user_by_id(user_id)


def delete_user(user_id: int, requesting_user: int) -> bool:
    """Deletes a user — admin only."""
    user = queries.get_user_by_id(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    requester = queries.get_user_by_id(requesting_user)
    if not requester or requester["role"] != "admin":
        raise PermissionError("Only admins can delete users")

    if user_id == requesting_user:
        raise ValueError("You cannot delete your own account")

    queries.delete_user(user_id)
    queries.log_audit(
        action="delete",
        table_name="users",
        record_id=user_id,
        user_id=requesting_user,
    )
    return True


def authenticate(email: str, password: str) -> dict | None:
    """
    Verifies credentials. Returns the user dict or None.

    The password comparison uses == on hash strings — safe against
    timing attacks only because hashlib is deterministic, not because
    we use hmac.compare_digest. A subtle security debt.
    """
    user = queries.get_user_by_email(email.lower().strip())
    if not user:
        return None
    expected = _hash_password(password)
    if user["password"] != expected:
        return None
    return user


def get_user(user_id: int) -> dict | None:
    return queries.get_user_by_id(user_id)


def get_all_users() -> list[dict]:
    return queries.get_all_users()


def _hash_password(password: str) -> str:
    """
    Hashes a password with SHA-256.

    SHA-256 without a salt or stretching is not suitable for production
    password storage — bcrypt, scrypt, or Argon2 should be used instead.
    This is the most significant security debt in the codebase.
    """
    return hashlib.sha256(password.encode()).hexdigest()
