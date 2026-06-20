from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_database_session
from app.models.report import Report
from app.models.workspace import Workspace
from app.schemas.answer import (
    AnswerRequest,
    AnswerResponse,
    CitationResponse,
    ReportResponse,
)
from app.services.generation import ANSWER_MODEL, generate_grounded_answer
from app.services.retrieval import retrieve_chunks

router = APIRouter(tags=["answers"])

@router.post(
    "/workspaces/{workspace_id}/answer",
    response_model=AnswerResponse,
)
def answer_workspace(
    workspace_id: int,
    answer_input: AnswerRequest,
    database_session: Session = Depends(get_database_session),
):
    workspace = database_session.get(Workspace, workspace_id)
    
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    retrieved_chunks = retrieve_chunks(
        database_session=database_session,
        workspace_id=workspace_id,
        query=answer_input.query,
        limit=answer_input.limit,
    )

    if not retrieved_chunks:
        raise HTTPException(
            status_code=404,
            detail="No searchable chunks were found in this workspace",
        )

    try:
        answer = generate_grounded_answer(
            query=answer_input.query,
            retrieved_chunks=retrieved_chunks,
        )
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail="Failed to generate an answer",
        ) from error
    
    report_id: int | None = None

    if answer_input.save_report:
        report = Report(
            workspace_id=workspace_id,
            query=answer_input.query,
            answer=answer,
            cited_chunk_ids=[
                chunk.chunk_id for chunk in retrieved_chunks   
            ],
            model_used=ANSWER_MODEL,
            retrieval_limit=answer_input.limit,
        )
    
        database_session.add(report)
        database_session.commit()
        database_session.refresh(report)

        report_id = report.id

    citations = [
        CitationResponse(
            citation_number=index,
            chunk_id=chunk.chunk_id,
            source_id=chunk.source_id,
            source_title=chunk.source_title,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            similarity=chunk.similarity,
        )
        for index, chunk in enumerate(retrieved_chunks, start=1)
    ]

    return AnswerResponse(
        report_id=report_id,
        answer=answer,
        citations=citations,
    )

@router.get(
    "/workspaces/{workspace_id}/reports",
    response_model=list[ReportResponse],
)

def list_reports(
    workspace_id: int,
    database_session: Session = Depends(get_database_session),
):
    workspace = database_session.get(Workspace, workspace_id)

    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    return (
        database_session.query(Report)
        .filter(Report.workspace_id == workspace_id)
        .order_by(Report.created_at.desc())
        .all()
    )
