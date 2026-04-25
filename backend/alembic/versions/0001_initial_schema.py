"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01

"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, list[str], None] = None
depends_on: Union[str, list[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    sa.Enum("low", "medium", "high", "critical", name="issue_severity").create(bind, checkfirst=True)
    sa.Enum("pending", "running", "completed", "failed", name="scan_status").create(bind, checkfirst=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("root_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("root_path"),
    )

    op.create_table(
        "logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_logs_level"), "logs", ["level"], unique=False)
    op.create_index(op.f("ix_logs_timestamp"), "logs", ["timestamp"], unique=False)

    op.create_table(
        "ai_insights",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_insights_project_id"), "ai_insights", ["project_id"], unique=False)

    op.create_table(
        "scan_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending", "running", "completed", "failed", name="scan_status", create_type=False
            ),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("source_root", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scan_runs_project_id"), "scan_runs", ["project_id"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_messages_project_id"), "chat_messages", ["project_id"], unique=False)

    op.create_table(
        "files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scan_run_id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=1024), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["scan_run_id"], ["scan_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scan_run_id", "path", name="uq_files_scan_path"),
    )
    op.create_index(op.f("ix_files_scan_run_id"), "files", ["scan_run_id"], unique=False)

    op.create_table(
        "apis",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scan_run_id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("method", sa.String(length=32), nullable=True),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("path_pattern", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_run_id"], ["scan_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scan_run_id",
            "method",
            "endpoint",
            "file_id",
            name="uq_api_scan_method_endpoint_file",
        ),
    )
    op.create_index(op.f("ix_apis_file_id"), "apis", ["file_id"], unique=False)
    op.create_index(op.f("ix_apis_scan_run_id"), "apis", ["scan_run_id"], unique=False)

    op.create_table(
        "api_calls",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("api_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("response_time_ms", sa.Float(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("is_error", sa.Boolean(), nullable=True),
        sa.Column("method", sa.String(length=32), nullable=True),
        sa.Column("path", sa.Text(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["api_id"], ["apis.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_calls_api_id"), "api_calls", ["api_id"], unique=False)
    op.create_index(op.f("ix_api_calls_method"), "api_calls", ["method"], unique=False)
    op.create_index(op.f("ix_api_calls_project_id"), "api_calls", ["project_id"], unique=False)
    op.create_index(op.f("ix_api_calls_timestamp"), "api_calls", ["timestamp"], unique=False)

    op.create_table(
        "snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("scan_run_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=256), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("label", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_run_id"], ["scan_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_snapshots_project_id"), "snapshots", ["project_id"], unique=False)
    op.create_index(op.f("ix_snapshots_scan_run_id"), "snapshots", ["scan_run_id"], unique=False)
    op.create_index(op.f("ix_snapshots_created_at"), "snapshots", ["created_at"], unique=False)

    op.create_table(
        "issues",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("api_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=128), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            postgresql.ENUM(
                "low",
                "medium",
                "high",
                "critical",
                name="issue_severity",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("resolved", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["api_id"], ["apis.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_issues_project_id"), "issues", ["project_id"], unique=False)
    op.create_index(op.f("ix_issues_api_id"), "issues", ["api_id"], unique=False)
    op.create_index(op.f("ix_issues_type"), "issues", ["type"], unique=False)
    op.create_index(op.f("ix_issues_created_at"), "issues", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("issues")
    op.drop_table("snapshots")
    op.drop_table("api_calls")
    op.drop_table("apis")
    op.drop_table("files")
    op.drop_table("chat_messages")
    op.drop_table("scan_runs")
    op.drop_index(op.f("ix_ai_insights_project_id"), table_name="ai_insights")
    op.drop_table("ai_insights")
    op.drop_index(op.f("ix_logs_timestamp"), table_name="logs")
    op.drop_index(op.f("ix_logs_level"), table_name="logs")
    op.drop_table("logs")
    op.drop_table("projects")
    op.execute("DROP TYPE IF EXISTS scan_status")
    op.execute("DROP TYPE IF EXISTS issue_severity")
