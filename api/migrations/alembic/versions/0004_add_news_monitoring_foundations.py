"""Add news monitoring configuration and run records.

Revision ID: 0004
Revises: 0003
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "news_search_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "frequency",
            sa.String(length=20),
            nullable=False,
            server_default="manual",
        ),
        sa.Column("run_at", sa.String(length=5), nullable=True),
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=False,
            server_default="UTC",
        ),
        sa.Column(
            "max_results_per_run",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "workspace_id",
            name="uq_news_search_configs_workspace_id",
        ),
    )
    op.create_index(
        "ix_news_search_configs_workspace_id",
        "news_search_configs",
        ["workspace_id"],
    )

    op.create_table(
        "news_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("query_used", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "articles_found",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "articles_processed",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "insights_created",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_news_runs_workspace_id",
        "news_runs",
        ["workspace_id"],
    )
    op.create_index(
        "ix_news_runs_created_at",
        "news_runs",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_news_runs_created_at", table_name="news_runs")
    op.drop_index("ix_news_runs_workspace_id", table_name="news_runs")
    op.drop_table("news_runs")

    op.drop_index(
        "ix_news_search_configs_workspace_id",
        table_name="news_search_configs",
    )
    op.drop_table("news_search_configs")
