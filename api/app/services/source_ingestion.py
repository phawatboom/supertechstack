from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.source import Source
from app.services.chunking import chunk_text
from app.services.embeddings import create_embeddings


def ingest_source_text(
    database_session: Session,
    workspace_id: int,
    title: str,
    raw_text: str,
    source_type: str,
    original_filename: str | None = None,
    mime_type: str | None = None,
    file_size: int | None = None,
) -> Source:
    normalized_title = title.strip()

    if not normalized_title:
        raise ValueError("Source title cannot be blank")

    chunk_contents = chunk_text(raw_text)

    if not chunk_contents:
        raise ValueError("Source text cannot be blank")

    try:
        chunk_embeddings = create_embeddings(chunk_contents)
    except Exception as error:
        raise RuntimeError("Failed to generate source embeddings") from error

    if len(chunk_embeddings) != len(chunk_contents):
        raise RuntimeError("Failed to generate embeddings for all chunks")

    source = Source(
        workspace_id=workspace_id,
        title=normalized_title,
        source_type=source_type,
        raw_text=raw_text,
        original_filename=original_filename,
        mime_type=mime_type,
        file_size=file_size,
        extraction_status="completed",
    )

    try:
        database_session.add(source)
        database_session.flush()
        database_session.add_all(
            [
                Chunk(
                    source_id=source.id,
                    workspace_id=workspace_id,
                    chunk_index=index,
                    content=chunk_content,
                    embedding=chunk_embeddings[index],
                )
                for index, chunk_content in enumerate(chunk_contents)
            ]
        )
        database_session.commit()
        database_session.refresh(source)
    except Exception:
        database_session.rollback()
        raise

    return source
