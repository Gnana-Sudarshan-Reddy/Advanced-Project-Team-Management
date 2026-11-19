# Advanced Project & Team Management System — Phase 2 Backend

FastAPI, SQLAlchemy and Alembic backend for the Phase 2 continuation of the existing Project & Team Management System.

## Features

- JWT authentication and role-based permissions for Admin, Project Manager and Team Member
- Projects, members, tasks, subtasks, milestones and project status workflows
- Task dependencies with duplicate and circular-dependency protection
- Task checklists, watchers, comments, replies, mentions and reactions
- Field-level task history through `GET /api/v1/tasks/{task_id}/history`
- Recurring daily, weekly and monthly tasks materialized by the background worker
- Task attachments with type/size validation and authenticated downloads
- Timer-based and manual time tracking
- Weekly timesheets and manager approval
- Project discussions, documents, approvals and calendar events
- In-app and WebSocket notifications with read/unread state and preferences
- Resource allocations, workload reports and project analytics
- Pagination, filtering, validation, audit activity and consistent error responses

## Requirements

- Python 3.11+
- SQLite for local development
- MySQL 8+ recommended for production

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`.

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- Health check: `/health`
- API prefix: `/api/v1`

The first administrator is seeded from `FIRST_ADMIN_EMAIL`, `FIRST_ADMIN_PASSWORD` and `FIRST_ADMIN_NAME`.
Change the default secret and administrator password before deploying.

## MySQL configuration

Set the following in `.env` for production-style usage:

```env
DATABASE_URL=mysql+pymysql://pm_user:pm_password@localhost:3306/project_management
SECRET_KEY=replace-with-a-long-random-secret
```

Run `alembic upgrade head` against the configured database. The migration chain currently contains the initial Phase 2 schema and the quality/integrity migration.

## Important API flows

### Authentication

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/users/me
```

Use the returned bearer token in the `Authorization` header.

### Task dependencies

```text
POST   /api/v1/task-dependencies
GET    /api/v1/task-dependencies?task_id={id}
DELETE /api/v1/task-dependencies/{dependency_id}
```

The API rejects self-dependencies, cross-project dependencies, duplicates and circular dependency chains. A task cannot be marked `done` while a prerequisite is incomplete.

### Task history

```text
GET /api/v1/tasks/{task_id}/history
```

History includes the action, changed fields, old/new values, actor and timestamp.

### Attachments

```text
POST /api/v1/task-attachments/{task_id}/upload
GET  /api/v1/task-attachments/{task_id}
GET  /api/v1/task-attachments/download/{attachment_id}
```

Uploaded files are restricted by MIME type and size, stored with generated names and served only after project-access validation.

### Time tracking

```text
POST /api/v1/time-entries/{task_id}/start
POST /api/v1/time-entries/{task_id}/stop
POST /api/v1/time-entries/{task_id}/manual
POST /api/v1/timesheets/me/{week_start_date}/submit
PATCH /api/v1/timesheets/{timesheet_id}/approve
```

### Notifications

```text
GET   /api/v1/notifications
PATCH /api/v1/notifications/{notification_id}/read
PATCH /api/v1/notifications/read-all
WS    /api/v1/notifications/ws?user_id={id}&token={jwt}
```

## Testing

Run the focused regression tests:

```powershell
python -m pytest -q tests
```

Run syntax validation:

```powershell
python -m compileall -q app alembic
```

## Demo sequence

1. Log in as the seeded administrator.
2. Create users and assign the three roles.
3. Create a project and add team members.
4. Create Task A, Task B and Task C.
5. Add A → B and B → C dependencies.
6. Attempt C → A and show the circular-dependency error.
7. Attempt to complete Task C before Task B and show the blocked-completion error.
8. Complete the prerequisite tasks and complete Task C.
9. Update a task and display its field-level history.
10. Upload a supported attachment, download it, then demonstrate rejected file types/sizes.
11. Start/stop a timer, submit a timesheet and approve it as a manager.
12. Add a watcher, update/comment on the task and demonstrate watcher notifications.
13. Open the analytics endpoints and show completion, workload, delay and time reports.

## Production follow-up

For a multi-worker deployment, move WebSocket connection coordination and recurring-task scheduling to shared infrastructure such as Redis/Celery. Add rate limiting, centralized file storage, antivirus scanning and a full integration-test suite before production release.
