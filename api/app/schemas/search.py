from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class SearchResultResponse(BaseModel):
    chunk_id: int
    source_id: int
    chunk_index: int
    content: str
    similarity: float
