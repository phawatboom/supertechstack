from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AnswerTrace(Base):
    __tablename__ = "answer_traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id"),
        nullable=False,
        index=True,
    )
    report_id: Mapped[int | None] = mapped_column(
        ForeignKey("reports.id"),
        nullable=True,
    )

    query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="started",
    )
    capture_content: Mapped[bool] = mapped_column(nullable=False, default=True)

    retrieved_chunks: Mapped[list[dict] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    model_input: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    openai_response_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    retrieval_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generation_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
