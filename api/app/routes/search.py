from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_database_session
from app.models.chunk import Chunk
from app.models.workspace import Workspace
from app.schemas.search import SearchRequest, SearchResultResponse
from app.services.embeddings import create_embedding

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

    query_embedding = create_embedding(search_input.query)

    if not query_embedding:
        raise HTTPException(status_code=422, detail="Search query cannot be blank")

    distance = Chunk.embedding.cosine_distance(query_embedding).label("distance")

    results = (
        database_session.query(Chunk, distance)
        .filter(Chunk.workspace_id == workspace_id)
        .filter(Chunk.embedding.isnot(None))
        .order_by(distance)
        .limit(search_input.limit)
        .all()
    )

    return [
        SearchResultResponse(
            chunk_id=chunk.id,
            source_id=chunk.source_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            similarity=1 - float(distance_value),
        )
        for chunk, distance_value in results
    ]
