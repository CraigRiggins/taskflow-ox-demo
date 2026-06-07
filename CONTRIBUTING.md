# Contributing to Taskflow

Taskflow is a demo application for [ox](https://github.com/CraigRiggins/ox) —
a tool that prevents technical debt at the point of introduction by reviewing
code changes as you make them.

**The whole point of this repo is to show ox in action.** Open a PR and watch
ox post inline review comments with specific findings and suggested fixes.

---

## How to contribute

### 1. Fork and clone

```bash
git clone https://github.com/CraigRiggins/taskflow-ox-demo
cd taskflow-ox-demo
pip install -e ".[dev]"
```

### 2. Pick something to work on

Check the [open issues](../../issues) for ideas. The best PRs for demonstrating
ox are ones that touch the core business logic:

| File | Why it's interesting for ox |
|---|---|
| `app/services/task_service.py` | High-churn hotspot — ox tracks every change here |
| `app/services/user_service.py` | Has duplicated validation ox will notice |
| `app/services/email_service.py` | Stub implementations waiting to be built |
| `app/routes/auth.py` | Boundary file — ox checks blast radius for auth changes |
| `app/db/queries.py` | Query complexity grows over time — ox spots it |

### 3. Make your change

Keep PRs small and focused — one feature or bug fix per PR. Larger PRs give
ox more to review but are harder to discuss.

Run tests before opening your PR:

```bash
pytest tests/ -v
```

### 4. Open a PR

Once your PR is open, ox will:

1. Detect the new PR via GitHub webhook
2. Download the codebase baseline (hotspot scores, conventions, call graph)
3. Analyse your diff against that baseline
4. Post inline review comments directly on the lines you changed

The comments include:
- The specific reason the finding matters for **this file** (not a generic rule)
- A suggested fix as a code block you can apply with one click
- The file's hotspot score (how much churn and complexity it has)

### 5. Respond to ox's findings

In your PR, note whether you accepted, edited, or skipped each ox finding and why.
This is the most valuable part of the demo — showing that ox surfaces actionable
findings developers can engage with, not just noise to dismiss.

---

## What ox is looking for

ox doesn't just run a linter. It reasons about your change in context:

- **Complexity** — does this change make an already-complex function harder to maintain?
- **Duplication** — does this code repeat logic that already exists elsewhere?
- **Coupling** — does this change create new dependencies between modules that shouldn't know about each other?
- **Convention** — does this follow the patterns the rest of the codebase uses?

The findings are specific to the file being changed, not generic warnings. If you
add code to `task_service.py` ox knows that file has changed 47 times in 90 days
and is imported by 12 other modules — so it weighs severity accordingly.

---

## Intentional debt in this codebase

Taskflow was written the way real production code evolves: working and tested, but
with shortcuts that accumulate over time. Some things ox will notice:

- Email validation logic is duplicated in three places
- `task_service.py::create_task` handles validation, business logic, audit logging,
  and notification triggering all in one function
- `user_service.py::_hash_password` uses SHA-256 without salting
- The in-memory token store in `auth.py` won't work across multiple processes
- Several TODO comments mark features that were never implemented

These are realistic forms of technical debt — not artificial bugs, but the kind
of thing that makes a codebase harder to maintain over time. ox is designed to
catch new debt as it's introduced, before it gets merged.

---

## Questions?

Open an issue or reach out — we're happy to help you set up a PR that makes for
a good ox demonstration.
