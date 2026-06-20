from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.chunk import Chunk
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

def retrieve_chunks(
    database_session: Session,
    workspace_id:int,
    query: str,
    limit: int, 
) -> list[RetrievedChunk]:
    query_embedding = create_embedding(query)

    if not query_embedding:
        return []
    
    distance = Chunk.embedding.cosine_distance(query_embedding).label("distance")

    rows = (
        database_session.query(Chunk, Source.title, distance)
        .join(Source, Source.id == Chunk.source_id)
        .filter(Chunk.workspace_id == workspace_id)
        .filter(Chunk.embedding.isnot(None))
        .order_by(distance)
        .limit(limit)
        .all()
    )

    return [
        RetrievedChunk(
            chunk_id=chunk.id,
            source_id=chunk.source_id,
            source_title=source_title,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            similarity=1 - float(distance_value),
        )
        for chunk, source_title, distance_value in rows
    ]
    