from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_database_session
from app.config import Settings, get_settings
from app.rate_limit import enforce_demo_embedding_limit, enforce_rate_limit
from app.schemas.search import SearchRequest, SearchResultResponse
from app.security import Principal, get_owned_workspace
from app.services.retrieval import retrieve_chunks

router = APIRouter(tags=["search"])


@router.post(
    "/workspaces/{workspace_id}/search",
    response_model=list[SearchResultResponse],
)
def search_workspace(
    workspace_id: int,
    search_input: SearchRequest,
    principal: Principal = Depends(enforce_rate_limit),
    settings: Settings = Depends(get_settings),
    database_session: Session = Depends(get_database_session),
):
    get_owned_workspace(workspace_id, principal, database_session)

    if (
        principal.is_demo
        and len(search_input.query) > settings.demo_max_query_chars
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Demo search queries are limited to "
                f"{settings.demo_max_query_chars} characters"
            ),
        )

    enforce_demo_embedding_limit(principal, settings)

    try:
        retrieved_chunks = retrieve_chunks(
            database_session=database_session,
            workspace_id=workspace_id,
            query=search_input.query,
            limit=(
                min(
                    search_input.limit,
                    settings.demo_max_retrieval_limit,
                )
                if principal.is_demo
                else search_input.limit
            ),
        )
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail="Failed to search workspace sources",
        ) from error

    return [
        SearchResultResponse(
            chunk_id=chunk.chunk_id,
            chunk_type=chunk.chunk_type,
            source_id=chunk.source_id,
            source_title=chunk.source_title,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            similarity=chunk.similarity,
        )
        for chunk in retrieved_chunks
    ]
