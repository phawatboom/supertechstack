from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.generation import (
    ANSWER_MODEL,
    DEFAULT_ANSWER_INSTRUCTIONS,
    DEFAULT_INPUT_TEMPLATE,
)
from app.config import get_settings

settings = get_settings()

class AnswerRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20_000)
    limit: int = Field(default=5, ge=1, le=settings.max_retrieval_limit)
    save_report: bool = True
    model: str = Field(default=ANSWER_MODEL, min_length=1, max_length=100)
    instructions: str = Field(
        default=DEFAULT_ANSWER_INSTRUCTIONS,
        min_length=1,
        max_length=20_000,
    )
    input_template: str = Field(
        default=DEFAULT_INPUT_TEMPLATE,
        min_length=1,
        max_length=50_000,
    )
    max_output_tokens: int | None = Field(
        default=None,
        ge=1,
        le=settings.max_output_tokens,
    )

    @field_validator("query", "model", "instructions", "input_template")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Value cannot be blank")

        return value

class CitationResponse(BaseModel):
    citation_number: int
    chunk_id: int
    source_id: int
    source_title: str
    chunk_index: int
    content: str
    similarity: float

class AnswerResponse(BaseModel):
    trace_id: str | None
    report_id: int | None
    answer: str
    citations: list[CitationResponse]


class AnswerDefaultsResponse(BaseModel):
    model: str
    instructions: str
    input_template: str
    retrieval_limit: int
    max_retrieval_limit: int
    max_output_tokens: int | None
    save_report: bool

class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    query: str
    answer: str
    cited_chunk_ids: list[int]
    model_used: str
    retrieval_limit: int
    created_at: datetime


class AnswerTraceSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: int
    report_id: int | None
    query: str
    status: str
    model_used: str | None
    retrieval_ms: int | None
    generation_ms: int | None
    total_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class AnswerTraceDetailResponse(AnswerTraceSummaryResponse):
    capture_content: bool
    retrieved_chunks: list[dict] | None
    model_input: dict | None
    model_output: dict | None
    openai_response_id: str | None
