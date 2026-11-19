"""Roles and permissions (RBAC). Permissions are stored on the Role row and are editable by Admin."""

class RoleName:
    """Canonical role names stored in the database."""

    ADMIN = "Admin"
    PROJECT_MANAGER = "Project Manager"
    TEAM_MEMBER = "Team Member"


class Perm:
    """Permission identifiers used by route access checks and role configuration."""

    USERS_MANAGE = "users:manage"
    USERS_READ = "users:read"
    ROLES_MANAGE = "roles:manage"
    PROJECTS_CREATE = "projects:create"
    PROJECTS_UPDATE = "projects:update"
    PROJECTS_DELETE = "projects:delete"
    PROJECTS_MEMBERS = "projects:manage_members"
    TASKS_CREATE = "tasks:create"
    TASKS_UPDATE = "tasks:update"
    TASKS_DELETE = "tasks:delete"
    TASKS_UPDATE_STATUS = "tasks:update_status"  # limited: only status of own assigned tasks
    COMMENTS_CREATE = "comments:create"
    ACTIVITY_READ_ALL = "activity:read_all"

    # ---------- Phase 2 permissions ----------
    MILESTONES_MANAGE = "milestones:manage"
    TASKS_MANAGE_DEPENDENCIES = "tasks:manage_dependencies"
    TASKS_MANAGE_SUBTASKS = "tasks:manage_subtasks"
    TASKS_MANAGE_ATTACHMENTS = "tasks:manage_attachments"
    TASKS_MANAGE_WATCHERS = "tasks:manage_watchers"
    TASKS_MANAGE_CHECKLISTS = "tasks:manage_checklists"
    TIME_TRACKING = "time:tracking"
    TIMESHEETS_MANAGE = "timesheets:manage"
    DISCUSSIONS_CREATE = "discussions:create"
    DISCUSSIONS_MANAGE = "discussions:manage"
    PROJECT_APPROVAL = "projects:approve"
    REPORTS_READ = "reports:read"
    RESOURCE_MANAGE = "resources:manage"
    CALENDAR_MANAGE = "calendar:manage"
    NOTIFICATIONS_READ_ALL = "notifications:read_all"


# Derive this list so permission validation stays aligned with the constants above.
ALL_PERMISSIONS: set[str] = {v for k, v in vars(Perm).items() if not k.startswith("_")}

# These defaults are applied only when a role is first seeded.
DEFAULT_ROLE_PERMISSIONS: dict[str, list[str]] = {
    RoleName.ADMIN: sorted(ALL_PERMISSIONS),
    RoleName.PROJECT_MANAGER: [
        Perm.USERS_READ, Perm.PROJECTS_CREATE, Perm.PROJECTS_UPDATE, Perm.PROJECTS_DELETE,
        Perm.PROJECTS_MEMBERS, Perm.TASKS_CREATE, Perm.TASKS_UPDATE, Perm.TASKS_DELETE,
        Perm.TASKS_UPDATE_STATUS, Perm.COMMENTS_CREATE,
        Perm.MILESTONES_MANAGE, Perm.TASKS_MANAGE_DEPENDENCIES, Perm.TASKS_MANAGE_SUBTASKS,
        Perm.TASKS_MANAGE_ATTACHMENTS, Perm.TASKS_MANAGE_WATCHERS, Perm.TASKS_MANAGE_CHECKLISTS,
        Perm.TIME_TRACKING, Perm.TIMESHEETS_MANAGE, Perm.DISCUSSIONS_CREATE,
        Perm.DISCUSSIONS_MANAGE, Perm.PROJECT_APPROVAL, Perm.REPORTS_READ,
        Perm.RESOURCE_MANAGE, Perm.CALENDAR_MANAGE,
    ],
    RoleName.TEAM_MEMBER: [
        Perm.TASKS_UPDATE_STATUS, Perm.COMMENTS_CREATE,
        Perm.TIME_TRACKING, Perm.DISCUSSIONS_CREATE,
    ],
}

ROLE_DESCRIPTIONS = {
    RoleName.ADMIN: "Full access to users, roles, projects and tasks",
    RoleName.PROJECT_MANAGER: "Creates projects, manages members, tasks and approvals",
    RoleName.TEAM_MEMBER: "Works on assigned tasks, records time and comments",
}