"""Add post versions, saves, and imports.

Revision ID: 0006
Revises: 0005
"""

from typing import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "post_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "post_id",
            sa.Integer(),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("markdown_content", sa.Text(), nullable=False),
        sa.Column("plain_text", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("cover_image_url", sa.String(length=2_000), nullable=True),
        sa.Column("visibility", sa.String(length=30), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=False),
        sa.Column(
            "is_available",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("disabled_reason", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "post_id",
            "version_number",
            name="uq_post_versions_post_id_version_number",
        ),
    )
    op.create_index("ix_post_versions_id", "post_versions", ["id"])
    op.create_index("ix_post_versions_post_id", "post_versions", ["post_id"])
    op.create_index("ix_post_versions_author_id", "post_versions", ["author_id"])

    op.create_table(
        "publication_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "post_version_id",
            sa.Integer(),
            sa.ForeignKey("post_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.VECTOR(dim=1536), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "post_version_id",
            "chunk_index",
            name="uq_publication_chunks_version_index",
        ),
    )
    op.create_index("ix_publication_chunks_id", "publication_chunks", ["id"])
    op.create_index(
        "ix_publication_chunks_post_version_id",
        "publication_chunks",
        ["post_version_id"],
    )

    op.create_table(
        "workspace_post_saves",
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "post_id",
            sa.Integer(),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("saved_by", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "post_id",
            name="uq_workspace_post_saves_workspace_post",
        ),
    )
    op.create_index(
        "ix_workspace_post_saves_saved_by",
        "workspace_post_saves",
        ["saved_by"],
    )

    op.create_table(
        "workspace_post_imports",
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "post_version_id",
            sa.Integer(),
            sa.ForeignKey("post_versions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("imported_by", sa.String(length=255), nullable=False),
        sa.Column(
            "imported_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "post_version_id",
            name="uq_workspace_post_imports_workspace_version",
        ),
    )
    op.create_index(
        "ix_workspace_post_imports_imported_by",
        "workspace_post_imports",
        ["imported_by"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workspace_post_imports_imported_by",
        table_name="workspace_post_imports",
    )
    op.drop_table("workspace_post_imports")
    op.drop_index(
        "ix_workspace_post_saves_saved_by",
        table_name="workspace_post_saves",
    )
    op.drop_table("workspace_post_saves")
    op.drop_index(
        "ix_publication_chunks_post_version_id",
        table_name="publication_chunks",
    )
    op.drop_index("ix_publication_chunks_id", table_name="publication_chunks")
    op.drop_table("publication_chunks")
    op.drop_index("ix_post_versions_author_id", table_name="post_versions")
    op.drop_index("ix_post_versions_post_id", table_name="post_versions")
    op.drop_index("ix_post_versions_id", table_name="post_versions")
    op.drop_table("post_versions")
