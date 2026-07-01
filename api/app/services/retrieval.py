from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.post import PostVersion, PublicationChunk, WorkspacePostImport
from app.models.source import Source
from app.services.embeddings import create_embedding

@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id:int
    source_id: int
    source_title: str
    chunk_index: int
    content: str
    similarity: float
    chunk_type: str = "source"

def retrieve_chunks(
    database_session: Session,
    workspace_id:int,
    query: str,
    limit: int, 
) -> list[RetrievedChunk]:
    query_embedding = create_embedding(query)

    if not query_embedding:
        return []
    
    source_distance = Chunk.embedding.cosine_distance(query_embedding).label("distance")

    source_rows = (
        database_session.query(Chunk, Source.title, source_distance)
        .join(Source, Source.id == Chunk.source_id)
        .filter(Chunk.workspace_id == workspace_id)
        .filter(Chunk.embedding.isnot(None))
        .order_by(source_distance)
        .limit(limit)
        .all()
    )

    publication_distance = PublicationChunk.embedding.cosine_distance(query_embedding).label(
        "distance"
    )
    publication_rows = (
        database_session.query(PublicationChunk, PostVersion, publication_distance)
        .join(
            WorkspacePostImport,
            WorkspacePostImport.post_version_id == PublicationChunk.post_version_id,
        )
        .join(PostVersion, PostVersion.id == PublicationChunk.post_version_id)
        .filter(WorkspacePostImport.workspace_id == workspace_id)
        .filter(PostVersion.is_available.is_(True))
        .filter(PublicationChunk.embedding.isnot(None))
        .order_by(publication_distance)
        .limit(limit)
        .all()
    )

    retrieved_chunks = [
        RetrievedChunk(
            chunk_id=chunk.id,
            source_id=chunk.source_id,
            source_title=source_title,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            similarity=1 - float(distance_value),
        )
        for chunk, source_title, distance_value in source_rows
    ] + [
        RetrievedChunk(
            chunk_id=chunk.id,
            source_id=-version.post_id,
            source_title=f"Imported post: {version.title}",
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            similarity=1 - float(distance_value),
            chunk_type="imported_post",
        )
        for chunk, version, distance_value in publication_rows
    ]

    retrieved_chunks.sort(key=lambda chunk: chunk.similarity, reverse=True)

    return retrieved_chunks[:limit]
    
