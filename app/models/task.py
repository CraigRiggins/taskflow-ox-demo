from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TaskCreate(BaseModel):
    title:       str            = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    status:      str            = Field("todo", pattern="^(todo|in_progress|review|done|cancelled)$")
    priority:    str            = Field("medium", pattern="^(low|medium|high|urgent)$")
    assignee_id: Optional[int] = None
    due_date:    Optional[str] = None
    tags:        Optional[str] = Field(None, max_length=500)


class TaskUpdate(BaseModel):
    title:       Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status:      Optional[str] = Field(None, pattern="^(todo|in_progress|review|done|cancelled)$")
    priority:    Optional[str] = Field(None, pattern="^(low|medium|high|urgent)$")
    assignee_id: Optional[int] = None
    due_date:    Optional[str] = None
    tags:        Optional[str] = None


class TaskResponse(BaseModel):
    id:          int
    title:       str
    description: Optional[str]
    status:      str
    priority:    str
    owner_id:    int
    assignee_id: Optional[int]
    due_date:    Optional[str]
    tags:        Optional[str]
    created_at:  str
    updated_at:  str


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    id:          int
    task_id:     int
    user_id:     int
    body:        str
    author_name: str
    created_at:  str
