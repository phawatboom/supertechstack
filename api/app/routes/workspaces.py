from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_database_session
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

@router.post("", response_model=WorkspaceResponse)
def create_workspace(
    workspace_input:WorkspaceCreate,
    database_session: Session = Depends(get_database_session),
):
    workspace = Workspace(
        name=workspace_input.name,
        description=workspace_input.description,
    )
    database_session.add(workspace)
    database_session.commit()
    database_session.refresh(workspace)

    return workspace

@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(
    database_session: Session = Depends(get_database_session),
):
    return database_session.query(Workspace).order_by(Workspace.created_at.desc()).all()

@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(
    workspace_id:int,
    database_session: Session = Depends(get_database_session),
):
    workspace = database_session.get(Workspace, workspace_id)

    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    return workspace

@router.delete("/{workspace_id}")
def delete_workspace(
    workspace_id:int,
    database_session: Session = Depends(get_database_session),
):
    workspace = database_session.get(Workspace, workspace_id)
    
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    database_session.delete(workspace)
    database_session.commit()
    return {"message": "workspace deleted"}