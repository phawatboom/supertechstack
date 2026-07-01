from pydantic import BaseModel, Field, field_validator

from app.config import get_settings

settings = get_settings()


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20_000)
    limit: int = Field(default=5, ge=1, le=settings.max_retrieval_limit)

    @field_validator("query")
    @classmethod
    def reject_blank_query(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Search query cannot be blank")

        return value


class SearchResultResponse(BaseModel):
    chunk_id: int
    chunk_type: str = "source"
    source_id: int
    source_title: str
    chunk_index: int
    content: str
    similarity: float
