from pydantic import BaseModel, Field
from app.config import get_settings

settings = get_settings()


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=settings.max_retrieval_limit)


class SearchResultResponse(BaseModel):
    chunk_id: int
    source_id: int
    source_title: str
    chunk_index: int
    content: str
    similarity: float
