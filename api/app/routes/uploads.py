from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_database_session
from app.models.workspace import Workspace
from app.schemas.source import SourceResponse
from app.services.file_extraction import (
    EmptyDocumentError,
    InvalidDocumentError,
    InvalidMimeTypeError,
    UnsupportedFileTypeError,
    extract_text_from_file,
)
from app.services.source_ingestion import ingest_source_text

router = APIRouter(tags=["uploads"])

MAX_FILE_SIZE = 20 * 1024 * 1024


@router.post(
    "/workspaces/{workspace_id}/uploads",
    response_model=SourceResponse,
)
async def upload_source(
    workspace_id: int,
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form(max_length=255)] = None,
    database_session: Session = Depends(get_database_session),
):
    workspace = database_session.get(Workspace, workspace_id)

    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    original_filename = Path(file.filename or "").name

    if not original_filename:
        raise HTTPException(
            status_code=422,
            detail="Uploaded file must have a filename",
        )

    content_type = file.content_type

    try:
        content = await file.read(MAX_FILE_SIZE + 1)
    finally:
        await file.close()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 20 MB limit",
        )

    if not content:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    try:
        extracted_file = extract_text_from_file(
            filename=original_filename,
            content=content,
            content_type=content_type,
        )
    except (UnsupportedFileTypeError, InvalidMimeTypeError) as error:
        raise HTTPException(status_code=415, detail=str(error)) from error
    except (InvalidDocumentError, EmptyDocumentError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    source_title = (
        (title or "").strip()
        or Path(original_filename).stem.strip()
        or original_filename
    )[:255]

    try:
        return ingest_source_text(
            database_session=database_session,
            workspace_id=workspace_id,
            title=source_title,
            raw_text=extracted_file.text,
            source_type=extracted_file.source_type,
            original_filename=original_filename[:255],
            mime_type=content_type,
            file_size=len(content),
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
