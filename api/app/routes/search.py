from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_database_session
from app.models.workspace import Workspace
from app.schemas.search import SearchRequest, SearchResultResponse
from app.services.retrieval import retrieve_chunks

router = APIRouter(tags=["search"])


@router.post(
    "/workspaces/{workspace_id}/search",
    response_model=list[SearchResultResponse],
)
def search_workspace(
    workspace_id: int,
    search_input: SearchRequest,
    database_session: Session = Depends(get_database_session),
):
    workspace = database_session.get(Workspace, workspace_id)

    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    retrieved_chunks = retrieve_chunks(
        database_session=database_session,
        workspace_id=workspace_id,
        query=search_input.query,
        limit=search_input.limit,
    )

    return [
        SearchResultResponse(
            chunk_id=chunk.chunk_id,
            source_id=chunk.source_id,
            source_title=chunk.source_title,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            similarity=chunk.similarity,
        )
        for chunk in retrieved_chunks
    ]
