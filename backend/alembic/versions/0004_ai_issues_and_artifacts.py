"""AI issues, scan artifacts, dependencies, patterns

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-27

"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, list[str], None] = None
depends_on: Union[str, list[str], None] = None


def upgrade() -> None:
    op.add_column("issues", sa.Column("source", sa.String(length=32), server_default="heuristic", nullable=False))
    op.add_column("issues", sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("issues", sa.Column("llm_model", sa.String(length=64), nullable=True))
    op.add_column("issues", sa.Column("external_url", sa.Text(), nullable=True))
    op.create_index(op.f("ix_issues_source"), "issues", ["source"], unique=False)

    op.add_column("apis", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_apis_content_hash"), "apis", ["content_hash"], unique=False)

    op.add_column("projects", sa.Column("alert_webhook_url", sa.Text(), nullable=True))
    op.add_column(
        "projects", sa.Column("github_app_installation_id", sa.String(length=64), nullable=True)
    )

    op.add_column("scan_runs", sa.Column("artifacts", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.create_table(
        "project_dependencies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scan_run_id", sa.Integer(), nullable=False),
        sa.Column("ecosystem", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("version", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["scan_run_id"], ["scan_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_project_dependencies_scan_run_id"),
        "project_dependencies",
        ["scan_run_id"],
        unique=False,
    )

    op.create_table(
        "issue_patterns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("issue_type", sa.String(length=128), nullable=False),
        sa.Column("hit_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "fingerprint", name="uq_issue_patterns_project_fingerprint"),
    )
    op.create_index(op.f("ix_issue_patterns_project_id"), "issue_patterns", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_issue_patterns_project_id"), table_name="issue_patterns")
    op.drop_table("issue_patterns")

    op.drop_index(op.f("ix_project_dependencies_scan_run_id"), table_name="project_dependencies")
    op.drop_table("project_dependencies")

    op.drop_column("scan_runs", "artifacts")

    op.drop_column("projects", "github_app_installation_id")
    op.drop_column("projects", "alert_webhook_url")

    op.drop_index(op.f("ix_apis_content_hash"), table_name="apis")
    op.drop_column("apis", "content_hash")

    op.drop_index(op.f("ix_issues_source"), table_name="issues")
    op.drop_column("issues", "external_url")
    op.drop_column("issues", "llm_model")
    op.drop_column("issues", "evidence")
    op.drop_column("issues", "source")
