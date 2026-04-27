"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "docks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(10), unique=True, nullable=False),
        sa.Column("dock_type", sa.String(20), server_default="standard"),
        sa.Column("status", sa.String(20), server_default="free"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "trucks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("license_plate", sa.String(20), unique=True, nullable=False),
        sa.Column("carrier_name", sa.String(100), nullable=False),
        sa.Column("cargo_type", sa.String(50), server_default="palletized"),
        sa.Column("cargo_volume_pallets", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(20), server_default="scheduled"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "staff",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), server_default="off_duty"),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "shifts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("staff.id"), nullable=False),
        sa.Column("shift_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("created_by", sa.String(50), server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("staff_id", "shift_date", "start_time", name="uq_shift_staff_date_time"),
    )

    op.create_table(
        "delivery_schedule",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("truck_id", sa.Integer(), sa.ForeignKey("trucks.id"), nullable=False),
        sa.Column("expected_arrival", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_arrival", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dock_id", sa.Integer(), sa.ForeignKey("docks.id"), nullable=True),
        sa.Column("estimated_unload_minutes", sa.Integer(), server_default="60"),
        sa.Column("status", sa.String(20), server_default="planned"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_delivery_schedule_expected_arrival", "delivery_schedule", ["expected_arrival"])

    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("schedule_entry_id", sa.Integer(), sa.ForeignKey("delivery_schedule.id"), nullable=False),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("staff.id"), nullable=False),
        sa.Column("dock_id", sa.Integer(), sa.ForeignKey("docks.id"), nullable=False),
        sa.Column("role_needed", sa.String(30), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_by", sa.String(50), server_default="manual"),
    )

    op.create_table(
        "agent_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_name", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(10), server_default="info"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_logs_created_at", "agent_logs", ["created_at"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(10), server_default="info"),
        sa.Column("is_read", sa.Boolean(), server_default="false"),
        sa.Column("source_agent", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_is_read_created_at", "notifications", ["is_read", "created_at"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("agent_logs")
    op.drop_table("assignments")
    op.drop_table("delivery_schedule")
    op.drop_table("shifts")
    op.drop_table("staff")
    op.drop_table("trucks")
    op.drop_table("docks")
