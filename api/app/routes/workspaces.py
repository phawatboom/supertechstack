from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.database import get_database_session
from app.models.workspace import Workspace
from app.rate_limit import enforce_rate_limit
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse
from app.security import Principal, get_owned_workspace

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("/demo/public", response_model=WorkspaceResponse)
def get_public_demo_workspace(
    settings: Settings = Depends(get_settings),
    database_session: Session = Depends(get_database_session),
):
    if not settings.demo_enabled:
        raise HTTPException(status_code=404, detail="Demo is not enabled")

    workspace = (
        database_session.query(Workspace)
        .filter(Workspace.owner_id == settings.demo_owner_id)
        .order_by(Workspace.id)
        .first()
    )

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Demo workspace has not been seeded",
        )

    return workspace

@router.post("", response_model=WorkspaceResponse)
def create_workspace(
    workspace_input:WorkspaceCreate,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=1,
        max_length=64,
    ),
):
    if idempotency_key is not None:
        existing_workspace = (
            database_session.query(Workspace)
            .filter(
                Workspace.owner_id == principal.owner_id,
                Workspace.creation_key == idempotency_key,
            )
            .first()
        )

        if existing_workspace is not None:
            return existing_workspace

    workspace = Workspace(
        owner_id=principal.owner_id,
        name=workspace_input.name,
        description=workspace_input.description,
        creation_key=idempotency_key,
    )
    database_session.add(workspace)
    try:
        database_session.commit()
    except IntegrityError:
        database_session.rollback()

        if idempotency_key is None:
            raise

        existing_workspace = (
            database_session.query(Workspace)
            .filter(
                Workspace.owner_id == principal.owner_id,
                Workspace.creation_key == idempotency_key,
            )
            .first()
        )

        if existing_workspace is None:
            raise

        return existing_workspace

    database_session.refresh(workspace)

    return workspace

@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    return (
        database_session.query(Workspace)
        .filter(Workspace.owner_id == principal.owner_id)
        .order_by(Workspace.created_at.desc())
        .all()
    )

@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(
    workspace_id:int,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    return get_owned_workspace(workspace_id, principal, database_session)

@router.delete("/{workspace_id}")
def delete_workspace(
    workspace_id:int,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    workspace = get_owned_workspace(
        workspace_id,
        principal,
        database_session,
    )
    
    database_session.delete(workspace)
    database_session.commit()
    return {"message": "workspace deleted"}
