---
name: Feature request / good first PR
about: Suggest a feature to add — great for demonstrating ox
title: "[FEATURE] "
labels: good first issue
---

## What feature would you like to add?

<!-- Describe the feature. Keep it small — a single endpoint or service method is ideal. -->

## Which files would you expect to touch?

<!-- 
Good areas to explore:
- app/services/task_service.py — the core hotspot. Any change here will trigger ox findings.
- app/services/user_service.py — has duplicated validation logic ox will notice.
- app/db/queries.py — adding a new query is a natural extension.
- app/routes/ — a new endpoint is always welcome.
-->

## Why would this be a good ox demo?

<!-- 
The best PRs for demonstrating ox are ones that:
1. Touch a file with a high hotspot score (task_service.py, auth.py)
2. Add new complexity to an already-complex function
3. Introduce a pattern that ox can compare against the team conventions

We intentionally left some features unimplemented so contributors can
add them and see what ox notices. Ideas:
- Add a /tasks/search endpoint that searches by title keyword
- Add task priority escalation (auto-upgrade priority when due date is near)
- Add a bulk status update endpoint (PATCH /tasks/bulk)
- Add pagination to GET /tasks
- Implement the email notifications (currently stubs in email_service.py)
- Add a /users/{id}/tasks endpoint that returns all tasks for a specific user
-->
