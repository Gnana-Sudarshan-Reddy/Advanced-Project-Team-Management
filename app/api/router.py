"""Combine endpoint routers into the application's versioned API."""

from fastapi import APIRouter

from app.api.routes import (
    activity, analytics, auth, calendar_events, comment_reactions, discussions,
    milestones, notifications, project_approvals, project_documents, resource_allocations, subtasks,
    projects, task_attachments, task_checklists, task_dependencies, task_watchers,
    tasks, teams, time_entries, timesheets, users,
)

api_router = APIRouter()
# Keep each feature's routes in its own module and register them here.
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(users.roles_router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(activity.router)

# ---------- Phase 2 routers ----------
api_router.include_router(milestones.router)
api_router.include_router(task_dependencies.router)
api_router.include_router(subtasks.router)
api_router.include_router(task_attachments.router)
api_router.include_router(task_watchers.router)
api_router.include_router(task_checklists.router)
api_router.include_router(time_entries.router)
api_router.include_router(timesheets.router)
api_router.include_router(discussions.router)
api_router.include_router(comment_reactions.router)
api_router.include_router(project_approvals.router)
api_router.include_router(notifications.router)
api_router.include_router(project_documents.router)
api_router.include_router(calendar_events.router)
api_router.include_router(resource_allocations.router)
api_router.include_router(analytics.router)
api_router.include_router(teams.router)
