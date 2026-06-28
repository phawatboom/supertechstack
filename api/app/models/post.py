from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "slug",
            name="uq_posts_workspace_id_slug",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id"),
        nullable=True,
        index=True,
    )
    author_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(String(2_000), nullable=True)
    visibility: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="private",
        server_default="private",
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="draft",
        server_default="draft",
    )

    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
