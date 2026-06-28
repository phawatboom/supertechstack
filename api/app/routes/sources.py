from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_database_session
from app.models.chunk import Chunk
from app.models.post import Post
from app.models.source import Source
from app.rate_limit import enforce_rate_limit
from app.schemas.source import (
    ChunkResponse,
    SourceCreate,
    SourceResponse,
    SourceUpdate,
)
from app.security import Principal, get_owned_workspace
from app.services.source_ingestion import ingest_source_text

router = APIRouter(tags=["sources"])


@router.post(
    "/workspaces/{workspace_id}/sources",
    response_model=SourceResponse,
)
def create_source(
    workspace_id: int,
    source_input: SourceCreate,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    get_owned_workspace(workspace_id, principal, database_session)

    try:
        return ingest_source_text(
            database_session=database_session,
            workspace_id=workspace_id,
            title=source_input.title,
            raw_text=source_input.raw_text,
            markdown_content=source_input.markdown_content,
            source_type="pasted_text",
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get(
    "/workspaces/{workspace_id}/sources",
    response_model=list[SourceResponse],
)
def list_sources(
    workspace_id: int,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    get_owned_workspace(workspace_id, principal, database_session)
    return (
        database_session.query(Source)
        .filter(Source.workspace_id == workspace_id)
        .order_by(Source.created_at.desc())
        .all()
    )


@router.patch(
    "/workspaces/{workspace_id}/sources/{source_id}",
    response_model=SourceResponse,
)
def update_source(
    workspace_id: int,
    source_id: int,
    source_input: SourceUpdate,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    get_owned_workspace(workspace_id, principal, database_session)
    source = (
        database_session.query(Source)
        .filter(Source.workspace_id == workspace_id, Source.id == source_id)
        .first()
    )

    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    changes = source_input.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(source, field, value)

    database_session.commit()
    database_session.refresh(source)

    return source


@router.delete(
    "/workspaces/{workspace_id}/sources/{source_id}",
)
def delete_source(
    workspace_id: int,
    source_id: int,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    get_owned_workspace(workspace_id, principal, database_session)
    source = (
        database_session.query(Source)
        .filter(Source.workspace_id == workspace_id, Source.id == source_id)
        .first()
    )

    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    deleted_chunks = (
        database_session.query(Chunk)
        .filter(Chunk.workspace_id == workspace_id, Chunk.source_id == source_id)
        .delete(synchronize_session=False)
    )
    (
        database_session.query(Post)
        .filter(Post.workspace_id == workspace_id, Post.source_id == source_id)
        .update({Post.source_id: None}, synchronize_session=False)
    )
    database_session.delete(source)
    database_session.commit()

    return {
        "message": "source deleted",
        "source_id": source_id,
        "deleted_chunks": deleted_chunks,
    }


@router.get(
    "/workspaces/{workspace_id}/chunks",
    response_model=list[ChunkResponse],
)
def list_chunks(
    workspace_id: int,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    get_owned_workspace(workspace_id, principal, database_session)
    return (
        database_session.query(Chunk)
        .filter(Chunk.workspace_id == workspace_id)
        .order_by(Chunk.source_id, Chunk.chunk_index)
        .all()
    )
