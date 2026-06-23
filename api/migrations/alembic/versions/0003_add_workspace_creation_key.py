"""Add idempotent workspace creation keys.

Revision ID: 0003
Revises: 0002
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column("creation_key", sa.String(length=64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_workspaces_owner_creation_key",
        "workspaces",
        ["owner_id", "creation_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_workspaces_owner_creation_key",
        "workspaces",
        type_="unique",
    )
    op.drop_column("workspaces", "creation_key")
