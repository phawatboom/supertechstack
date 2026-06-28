from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class SourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    raw_text: str = Field(min_length=1)
    markdown_content: str | None = Field(default=None, min_length=1)


class SourceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def strip_optional_title(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Value cannot be blank")

        return value

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        return self

class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id:int
    workspace_id: int
    title: str
    source_type: str
    raw_text: str
    markdown_content: str
    plain_text: str
    original_filename: str | None
    mime_type: str | None
    file_size: int | None
    extraction_status: str
    created_at: datetime

class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    workspace_id: int
    chunk_index: int
    content: str
    created_at: datetime

