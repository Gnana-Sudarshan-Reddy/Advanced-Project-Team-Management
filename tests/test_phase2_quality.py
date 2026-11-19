"""Focused regression tests for the Phase 2 backend improvements."""

from datetime import date

from app.api.routes.projects import ALLOWED_PROJECT_TRANSITIONS
from app.api.routes.task_dependencies import _would_create_cycle
from app.models.enums import ProjectStatus
from app.services.recurring_tasks import _next_date


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class _Db:
    def __init__(self, rows):
        self.rows = rows

    def query(self, *_args):
        return _Query(self.rows)


def test_dependency_cycle_detection():
    # 1 -> 2 -> 3, so adding 3 -> 1 must be rejected.
    assert _would_create_cycle(_Db([(1, 2), (2, 3)]), 3, 1) is True
    assert _would_create_cycle(_Db([(1, 2), (2, 3)]), 1, 3) is False


def test_monthly_recurrence_clamps_end_of_month():
    assert _next_date(date(2026, 1, 31), "monthly") == date(2026, 2, 28)


def test_project_workflow_does_not_skip_from_archived():
    assert ALLOWED_PROJECT_TRANSITIONS[ProjectStatus.ARCHIVED.value] == set()
    assert ProjectStatus.COMPLETED.value in ALLOWED_PROJECT_TRANSITIONS[ProjectStatus.ACTIVE.value]
