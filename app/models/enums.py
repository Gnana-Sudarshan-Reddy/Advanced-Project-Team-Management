"""Allowed status and priority values used by API validation and the database."""

from enum import Enum


class ProjectStatus(str, Enum):
    """Lifecycle states a project can move through."""

    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectHealth(str, Enum):
    """Computed/managed health indicator for a project."""

    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    DELAYED = "delayed"


class TaskStatus(str, Enum):
    """Workflow states available for a task."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class TaskPriority(str, Enum):
    """Relative urgency levels available for a task."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MilestoneStatus(str, Enum):
    """Lifecycle states for a project milestone."""

    UPCOMING = "upcoming"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"


class ApprovalStatus(str, Enum):
    """Possible states of a project approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TimesheetStatus(str, Enum):
    """Possible states of a timesheet."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class NotificationType(str, Enum):
    """Categories of notifications sent to users."""

    TASK_ASSIGNED = "task_assigned"
    DEADLINE_APPROACHING = "deadline_approaching"
    MENTION = "mention"
    COMMENT_ADDED = "comment_added"
    APPROVAL_REQUESTED = "approval_requested"
    TIMESHEET_SUBMITTED = "timesheet_submitted"
    TASK_REASSIGNED = "task_reassigned"
