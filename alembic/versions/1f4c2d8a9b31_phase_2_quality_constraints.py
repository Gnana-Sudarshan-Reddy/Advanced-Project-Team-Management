"""Add recurring task state, task history, and integrity constraints."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1f4c2d8a9b31"
down_revision: Union[str, Sequence[str], None] = "8eb38e611688"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("recurrence_next_date", sa.Date(), nullable=True))
        batch_op.create_index("ix_tasks_recurrence_next_date", ["recurrence_next_date"], unique=False)

    op.create_table(
        "task_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("changed_by_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_history_task_id", "task_history", ["task_id"])
    op.create_index("ix_task_history_changed_by_id", "task_history", ["changed_by_id"])
    op.create_index("ix_task_history_action", "task_history", ["action"])
    op.create_index("ix_task_history_created_at", "task_history", ["created_at"])

    with op.batch_alter_table("task_dependencies", schema=None) as batch_op:
        batch_op.create_unique_constraint("uq_task_dependency", ["task_id", "depends_on_task_id"])
    with op.batch_alter_table("timesheets", schema=None) as batch_op:
        batch_op.create_unique_constraint("uq_timesheet_user_week", ["user_id", "week_start_date"])


def downgrade() -> None:
    with op.batch_alter_table("timesheets", schema=None) as batch_op:
        batch_op.drop_constraint("uq_timesheet_user_week", type_="unique")
    with op.batch_alter_table("task_dependencies", schema=None) as batch_op:
        batch_op.drop_constraint("uq_task_dependency", type_="unique")
    op.drop_index("ix_task_history_created_at", table_name="task_history")
    op.drop_index("ix_task_history_action", table_name="task_history")
    op.drop_index("ix_task_history_changed_by_id", table_name="task_history")
    op.drop_index("ix_task_history_task_id", table_name="task_history")
    op.drop_table("task_history")
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.drop_index("ix_tasks_recurrence_next_date")
        batch_op.drop_column("recurrence_next_date")
