from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base

class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            "creation_key",
            name="uq_workspaces_owner_creation_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    creation_key: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
    )

# mapped_column() creates tge actual databse column

# select * from workspaces where id = 1;
# workspace = database_session.get(Workspace, 1)
