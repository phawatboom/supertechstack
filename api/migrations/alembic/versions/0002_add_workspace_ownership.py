"""Add workspace ownership.

Revision ID: 0002
Revises: 0001
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column("owner_id", sa.String(length=255), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE workspaces "
            "SET owner_id = 'beta-user' "
            "WHERE owner_id IS NULL"
        )
    )
    op.alter_column("workspaces", "owner_id", nullable=False)
    op.create_index(
        "ix_workspaces_owner_id",
        "workspaces",
        ["owner_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_workspaces_owner_id", table_name="workspaces")
    op.drop_column("workspaces", "owner_id")
