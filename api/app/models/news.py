from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class NewsSearchConfig(Base):
    __tablename__ = "news_search_configs"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            name="uq_news_search_configs_workspace_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    frequency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="manual",
    )
    run_at: Mapped[str | None] = mapped_column(String(5), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="UTC",
    )
    max_results_per_run: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class NewsRun(Base):
    __tablename__ = "news_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query_used: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
    )
    articles_found: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    articles_processed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    insights_created: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
