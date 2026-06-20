from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

class AnswerRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=10)
    save_report: bool = True

class CitationResponse(BaseModel):
    citation_number: int
    chunk_id: int
    source_id: int
    source_title: str
    chunk_index: int
    content: str
    similarity: float

class AnswerResponse(BaseModel):
    report_id: int | None
    answer: str
    citations: list[CitationResponse]

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