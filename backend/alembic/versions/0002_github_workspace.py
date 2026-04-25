"""GitHub fields and workspace; relax root_path unique

Revision ID: 0002
Revises: 0001
Create Date: 2025-04-23

"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, list[str], None] = None
depends_on: Union[str, list[str], None] = None


def upgrade() -> None:
    op.drop_constraint("projects_root_path_key", "projects", type_="unique")
    op.add_column("projects", sa.Column("github_repo_url", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("default_branch", sa.String(length=255), server_default="main", nullable=True))
    op.add_column("projects", sa.Column("last_commit_sha", sa.String(length=64), nullable=True))
    op.add_column(
        "projects",
        sa.Column("last_sync_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )
    op.execute(
        """
        CREATE UNIQUE INDEX ix_projects_github_repo_url_unique
        ON projects (github_repo_url)
        WHERE github_repo_url IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_projects_github_repo_url_unique")
    op.drop_column("projects", "last_sync_at")
    op.drop_column("projects", "last_commit_sha")
    op.drop_column("projects", "default_branch")
    op.drop_column("projects", "github_repo_url")
    op.create_unique_constraint("projects_root_path_key", "projects", ["root_path"])
