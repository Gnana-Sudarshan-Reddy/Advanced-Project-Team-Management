"""Import and re-export every ORM model so SQLAlchemy registers its tables."""

from app.models.activity import ActivityLog
from app.models.calendar_event import CalendarEvent
from app.models.comment import TaskComment
from app.models.discussion import ProjectDiscussion, DiscussionReply
from app.models.milestone import ProjectMilestone
from app.models.notification import Notification, NotificationPreference
from app.models.project import Project, ProjectMember
from app.models.project_approval import ProjectApproval
from app.models.resource_allocation import ResourceAllocation
from app.models.project_document import ProjectDocument
from app.models.task import Task
from app.models.task_history import TaskHistory
from app.models.task_attachment import TaskAttachment
from app.models.task_checklist import TaskChecklist
from app.models.task_dependency import TaskDependency
from app.models.task_watcher import TaskWatcher
from app.models.time_entry import TimeEntry
from app.models.timesheet import Timesheet
from app.models.user import Role, User
from app.models.comment_reaction import CommentReaction

__all__ = [
    "ActivityLog", "TaskComment", "Project", "ProjectMember", "Task", "Role", "User",
    "ProjectMilestone", "TaskDependency", "TaskAttachment", "TaskWatcher", "TaskChecklist",
    "TimeEntry", "Timesheet", "ProjectDiscussion", "DiscussionReply", "CommentReaction",
    "ProjectApproval", "Notification", "NotificationPreference", "CalendarEvent", "ResourceAllocation",
    "ProjectDocument", "TaskHistory",
]
