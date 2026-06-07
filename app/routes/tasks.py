"""Task management routes."""

from fastapi import APIRouter, HTTPException, Depends, Header, Query
from typing import Optional

from app.models.task import TaskCreate, TaskUpdate, TaskResponse, CommentCreate
from app.services import task_service
from app.routes.auth import require_auth

router = APIRouter()


@router.get("/")
def list_tasks(
    status:        Optional[str] = Query(None),
    priority:      Optional[str] = Query(None),
    tag:           Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
):
    """Returns all tasks visible to the current user."""
    user = require_auth(authorization)
    try:
        return task_service.get_tasks(
            user_id=user["id"],
            status=status,
            priority=priority,
            tag=tag,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/", status_code=201)
def create_task(
    body:          TaskCreate,
    authorization: Optional[str] = Header(None),
):
    """Creates a new task owned by the current user."""
    user = require_auth(authorization)
    try:
        return task_service.create_task(
            title=body.title,
            owner_id=user["id"],
            description=body.description or "",
            status=body.status,
            priority=body.priority,
            assignee_id=body.assignee_id,
            due_date=body.due_date,
            tags=body.tags or "",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats")
def task_stats(authorization: Optional[str] = Header(None)):
    """Returns aggregate task statistics for the current user."""
    user = require_auth(authorization)
    return task_service.get_task_stats(user["id"])


@router.get("/{task_id}")
def get_task(
    task_id:       int,
    authorization: Optional[str] = Header(None),
):
    """Returns a single task by ID."""
    require_auth(authorization)
    from app.db import queries
    task = queries.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}")
def update_task(
    task_id:       int,
    body:          TaskUpdate,
    authorization: Optional[str] = Header(None),
):
    """Updates a task. Only the owner or an admin may update."""
    user = require_auth(authorization)
    try:
        return task_service.update_task(
            task_id=task_id,
            user_id=user["id"],
            **body.model_dump(exclude_none=True),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id:       int,
    authorization: Optional[str] = Header(None),
):
    """Deletes a task. Only the owner or an admin may delete."""
    user = require_auth(authorization)
    try:
        task_service.delete_task(task_id, user["id"])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/{task_id}/comments")
def list_comments(
    task_id:       int,
    authorization: Optional[str] = Header(None),
):
    """Returns all comments on a task."""
    require_auth(authorization)
    from app.db import queries
    task = queries.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return queries.get_comments_for_task(task_id)


@router.post("/{task_id}/comments", status_code=201)
def add_comment(
    task_id:       int,
    body:          CommentCreate,
    authorization: Optional[str] = Header(None),
):
    """Adds a comment to a task."""
    user = require_auth(authorization)
    try:
        return task_service.add_comment(task_id, user["id"], body.body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
