from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base

class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pasted_text",
        server_default="pasted_text",
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    original_filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    mime_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    file_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    extraction_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="completed",
        server_default="completed",
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
