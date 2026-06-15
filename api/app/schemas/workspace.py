from datetime import datetime

from pydantic import BaseModel, ConfigDict

class WorkspaceCreate(BaseModel):
    name:str
    description: str | None = None

class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:int
    name:str
    description:str | None
    created_at:datetime
    updated_at: datetime

# anyclass that inherits from BaseModel becomes a data validation model