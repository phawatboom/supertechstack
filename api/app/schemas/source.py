from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

class SourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    raw_text: str = Field(min_length=1)
    markdown_content: str | None = Field(default=None, min_length=1)

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

