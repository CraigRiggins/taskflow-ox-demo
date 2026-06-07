"""User management routes."""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional

from app.models.user import UserCreate, UserUpdate, UserResponse
from app.services import user_service
from app.routes.auth import require_auth, require_admin

router = APIRouter()


@router.post("/", status_code=201)
def create_user(body: UserCreate):
    """Registers a new user. Public endpoint."""
    try:
        user = user_service.create_user(
            email=body.email,
            name=body.name,
            password=body.password,
            role=body.role,
        )
        return {k: v for k, v in user.items() if k != "password"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
def list_users(authorization: Optional[str] = Header(None)):
    """Returns all users. Admin only."""
    require_admin(authorization)
    users = user_service.get_all_users()
    return [{k: v for k, v in u.items() if k != "password"} for u in users]


@router.get("/{user_id}")
def get_user(
    user_id:       int,
    authorization: Optional[str] = Header(None),
):
    """Returns a user by ID."""
    require_auth(authorization)
    user = user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {k: v for k, v in user.items() if k != "password"}


@router.patch("/{user_id}")
def update_user(
    user_id:       int,
    body:          UserUpdate,
    authorization: Optional[str] = Header(None),
):
    """Updates a user profile. Self or admin only."""
    requester = require_auth(authorization)
    try:
        updated = user_service.update_user(
            user_id=user_id,
            requesting_user=requester["id"],
            **body.model_dump(exclude_none=True),
        )
        return {k: v for k, v in updated.items() if k != "password"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id:       int,
    authorization: Optional[str] = Header(None),
):
    """Deletes a user. Admin only."""
    requester = require_admin(authorization)
    try:
        user_service.delete_user(user_id, requester["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
