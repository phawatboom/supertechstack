from datetime import datetime

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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


class PostVersion(Base):
    __tablename__ = "post_versions"
    __table_args__ = (
        UniqueConstraint(
            "post_id",
            "version_number",
            name="uq_post_versions_post_id_version_number",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    author_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)
    plain_text: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(String(2_000), nullable=True)
    visibility: Mapped[str] = mapped_column(String(30), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    disabled_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PublicationChunk(Base):
    __tablename__ = "publication_chunks"
    __table_args__ = (
        UniqueConstraint(
            "post_version_id",
            "chunk_index",
            name="uq_publication_chunks_version_index",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    post_version_id: Mapped[int] = mapped_column(
        ForeignKey("post_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(VECTOR(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WorkspacePostSave(Base):
    __tablename__ = "workspace_post_saves"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "post_id",
            name="uq_workspace_post_saves_workspace_post",
        ),
    )

    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    saved_by: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WorkspacePostImport(Base):
    __tablename__ = "workspace_post_imports"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "post_version_id",
            name="uq_workspace_post_imports_workspace_version",
        ),
    )

    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )
    post_version_id: Mapped[int] = mapped_column(
        ForeignKey("post_versions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    imported_by: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
