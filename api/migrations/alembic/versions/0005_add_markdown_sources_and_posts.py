"""Add source Markdown representations and posts.

Revision ID: 0005
Revises: 0004
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("markdown_content", sa.Text(), nullable=True))
    op.add_column("sources", sa.Column("plain_text", sa.Text(), nullable=True))
    op.execute("UPDATE sources SET markdown_content = raw_text WHERE markdown_content IS NULL")
    op.execute("UPDATE sources SET plain_text = raw_text WHERE plain_text IS NULL")
    op.alter_column("sources", "markdown_content", nullable=False)
    op.alter_column("sources", "plain_text", nullable=False)

    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("sources.id"),
            nullable=True,
        ),
        sa.Column("author_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("markdown_content", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("cover_image_url", sa.String(length=2_000), nullable=True),
        sa.Column(
            "visibility",
            sa.String(length=30),
            nullable=False,
            server_default="private",
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("published_at", sa.DateTime(), nullable=True),
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
            "slug",
            name="uq_posts_workspace_id_slug",
        ),
    )
    op.create_index("ix_posts_id", "posts", ["id"])
    op.create_index("ix_posts_author_id", "posts", ["author_id"])
    op.create_index("ix_posts_source_id", "posts", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_posts_source_id", table_name="posts")
    op.drop_index("ix_posts_author_id", table_name="posts")
    op.drop_index("ix_posts_id", table_name="posts")
    op.drop_table("posts")
    op.drop_column("sources", "plain_text")
    op.drop_column("sources", "markdown_content")
