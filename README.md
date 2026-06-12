# Taskflow — ox demo application

A simple task management REST API, intentionally written the way real production
code evolves: working and tested, but with accumulated shortcuts and complexity
that a thoughtful code reviewer would flag.

**This repo exists to demonstrate [ox](https://github.com/CraigRiggins/ox)** —
a tool that reviews your code changes for technical debt as you make them, posting
inline PR comments with specific findings and suggested fixes.

Open a PR to see it in action.

---

## What is ox?

ox (short for antioxidant) prevents technical debt at the point of introduction.
When you open a pull request, ox:

1. Reads your diff and the surrounding codebase context
2. Checks which files you changed against the hotspot model
3. Retrieves relevant examples from the existing codebase
4. Posts inline review comments on the specific lines that introduce debt, with
   concrete suggested fixes

The findings are specific to your change and this codebase — not generic lint
warnings. If you add a function to `task_service.py`, ox knows that file has
changed frequently and is imported by many other modules, and it weighs its
findings accordingly.

---

## Try it yourself

### Make a change and open a PR

Clone the repo make a change to one of the files below, and open a PR against
the `main` branch. Good places to start:

```bash
git clone https://github.com/CraigRiggins/taskflow-ox-demo
cd taskflow-ox-demo
pip install -e ".[dev]"

# make a change — see suggestions below
# then:
git checkout -b my-feature
git add .
git commit -m "feat: add task search endpoint"
git push origin my-feature
# open PR on GitHub
```

### Suggested changes that produce interesting ox findings

**Add a search endpoint** — add `GET /tasks/search?q=keyword` to `app/routes/tasks.py`
and a corresponding query in `app/db/queries.py`. ox will notice if the search
logic duplicates existing filter patterns.

**Add pagination** — `GET /tasks` currently returns all tasks. Add `?page=1&limit=20`
pagination. ox will notice if the pagination logic isn't consistent with how
other list endpoints work.

**Implement email notifications** — `app/services/email_service.py` has stub
functions that currently just log to memory. Implement real SMTP sending.
ox will notice the email validation logic is already duplicated in three places.

**Add bulk status update** — add `PATCH /tasks/bulk` that accepts a list of task
IDs and a new status. ox will notice if the validation logic differs from
`task_service.py::update_task`.

**Add task priority escalation** — add a background job that auto-escalates task
priority when the due date is within 24 hours. ox will notice coupling between
the scheduling logic and the task service.

---

## Running locally

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

```bash
# run tests
pytest tests/ -v
```

---

## Codebase overview

```
app/
  main.py              FastAPI app, middleware, route registration
  routes/
    tasks.py           Task CRUD endpoints
    users.py           User management endpoints
    auth.py            Login, logout, token validation
  models/
    task.py            Pydantic request/response models
    user.py            User models and validators
  services/
    task_service.py    Task business logic  ← primary hotspot
    user_service.py    User business logic  ← has duplicated validation
    email_service.py   Notification stubs   ← good place to contribute
  db/
    connection.py      SQLite connection management
    queries.py         Raw database queries
tests/
  test_tasks.py        Task service unit tests
  test_auth.py        Auth integration tests
```

### Known technical debt (intentional)

These are realistic forms of debt that ox is designed to detect and flag in PRs:

| Location | Debt | Why it matters |
|---|---|---|
| `task_service.py::create_task` | Handles validation, business logic, audit, and notifications in one 80-line function | Single responsibility violation — hard to test and extend |
| `task_service.py::update_task` | ~100 lines, same issue | Same problem, compounded by permission checks |
| `user_service.py` + `models/user.py` + `email_service.py` | Email validation regex duplicated in three places | Any change to the rule must be made three times |
| `user_service.py::_hash_password` | SHA-256 without salting | Not suitable for production password storage |
| `auth.py::_tokens` | In-memory token store | Lost on restart, not shared across processes |
| `db/queries.py::get_tasks_for_user` | Builds WHERE clause by string concatenation | Harder to maintain as filter options grow |

ox will catch new debt added in PRs — the existing debt is the baseline it
learns from during onboarding.

---

## License

MIT
