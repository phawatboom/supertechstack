from datetime import datetime

from pydantic import BaseModel, ConfigDict

class SourceCreate(BaseModel):
    title: str
    raw_text: str

class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id:int
    workspace_id: int
    title: str
    source_type: str
    raw_text: str
    created_at: datetime

class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    workspace_id: int
    chunk_index: int
    content: str
    created_at: datetime

