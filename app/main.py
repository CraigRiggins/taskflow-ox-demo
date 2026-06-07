"""
Taskflow API — a simple task management REST API.

This is the ox demo application. The codebase is intentionally written
the way real production code evolves over time: working, tested, but with
accumulated shortcuts and complexity that a code reviewer would flag.

Open a PR to see ox in action.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import tasks, users, auth
from app.db.connection import init_db

app = FastAPI(
    title="Taskflow API",
    description="Simple task management API — ox demo application",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router, prefix="/tasks",  tags=["tasks"])
app.include_router(users.router, prefix="/users",  tags=["users"])
app.include_router(auth.router,  prefix="/auth",   tags=["auth"])


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
