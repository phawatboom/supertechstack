import os
from datetime import datetime
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_database_session
from app.models.answer_trace import AnswerTrace
from app.models.report import Report
from app.models.workspace import Workspace
from app.schemas.answer import (
    AnswerRequest,
    AnswerResponse,
    AnswerDefaultsResponse,
    AnswerTraceDetailResponse,
    AnswerTraceSummaryResponse,
    CitationResponse,
    ReportResponse,
)
from app.services.generation import (
    ANSWER_MODEL,
    DEFAULT_ANSWER_INSTRUCTIONS,
    DEFAULT_INPUT_TEMPLATE,
    build_generation_request,
    generate_grounded_answer,
)
from app.services.retrieval import RetrievedChunk, retrieve_chunks

router = APIRouter(tags=["answers"])


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


OBSERVABILITY_ENABLED = _env_flag("OBSERVABILITY_ENABLED", True)
OBSERVABILITY_CAPTURE_CONTENT = _env_flag(
    "OBSERVABILITY_CAPTURE_CONTENT",
    True,
)


@router.get(
    "/answer-settings/defaults",
    response_model=AnswerDefaultsResponse,
)
def get_answer_defaults():
    return AnswerDefaultsResponse(
        model=ANSWER_MODEL,
        instructions=DEFAULT_ANSWER_INSTRUCTIONS,
        input_template=DEFAULT_INPUT_TEMPLATE,
        retrieval_limit=5,
        max_retrieval_limit=20,
        max_output_tokens=None,
        save_report=True,
    )


def _elapsed_ms(started_at: float) -> int:
    return max(0, round((perf_counter() - started_at) * 1000))


def _serialize_retrieved_chunks(
    retrieved_chunks: list[RetrievedChunk],
    capture_content: bool,
) -> list[dict]:
    return [
        {
            "citation_number": index,
            "chunk_id": chunk.chunk_id,
            "source_id": chunk.source_id,
            "source_title": chunk.source_title,
            "chunk_index": chunk.chunk_index,
            "similarity": chunk.similarity,
            **({"content": chunk.content} if capture_content else {}),
        }
        for index, chunk in enumerate(retrieved_chunks, start=1)
    ]


def _mark_trace_failed(
    database_session: Session,
    trace_id: str | None,
    total_started_at: float,
    error: Exception | str,
) -> None:
    if trace_id is None:
        return

    database_session.rollback()
    trace = database_session.get(AnswerTrace, trace_id)

    if trace is None:
        return

    trace.status = "failed"
    trace.error_message = str(error)
    trace.total_ms = _elapsed_ms(total_started_at)
    trace.completed_at = datetime.utcnow()

    try:
        database_session.commit()
    except Exception:
        database_session.rollback()


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

    total_started_at = perf_counter()
    trace: AnswerTrace | None = None

    if OBSERVABILITY_ENABLED:
        trace = AnswerTrace(
            id=str(uuid4()),
            workspace_id=workspace_id,
            query=(
                answer_input.query
                if OBSERVABILITY_CAPTURE_CONTENT
                else "[content capture disabled]"
            ),
            status="started",
            capture_content=OBSERVABILITY_CAPTURE_CONTENT,
        )
        database_session.add(trace)
        database_session.commit()

    retrieval_started_at = perf_counter()

    try:
        retrieved_chunks = retrieve_chunks(
            database_session=database_session,
            workspace_id=workspace_id,
            query=answer_input.query,
            limit=answer_input.limit,
        )
    except Exception as error:
        _mark_trace_failed(
            database_session,
            trace.id if trace else None,
            total_started_at,
            error,
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to retrieve workspace evidence",
        ) from error

    retrieval_ms = _elapsed_ms(retrieval_started_at)

    if trace:
        trace.retrieval_ms = retrieval_ms
        trace.retrieved_chunks = _serialize_retrieved_chunks(
            retrieved_chunks,
            trace.capture_content,
        )
        trace.status = "retrieved"
        database_session.commit()

    if not retrieved_chunks:
        message = "No searchable chunks were found in this workspace"
        _mark_trace_failed(
            database_session,
            trace.id if trace else None,
            total_started_at,
            message,
        )
        raise HTTPException(status_code=404, detail=message)

    generation_request = build_generation_request(
        query=answer_input.query,
        retrieved_chunks=retrieved_chunks,
        model=answer_input.model,
        instructions=answer_input.instructions,
        input_template=answer_input.input_template,
        max_output_tokens=answer_input.max_output_tokens,
    )

    if trace:
        trace.model_used = generation_request.model
        trace.model_input = {
            "model": generation_request.model,
            "instructions": generation_request.instructions,
            "input_template": generation_request.input_template,
            "max_output_tokens": generation_request.max_output_tokens,
            **(
                {"input": generation_request.input_text}
                if trace.capture_content
                else {"input": "[content capture disabled]"}
            ),
        }
        trace.status = "generating"
        database_session.commit()

    generation_started_at = perf_counter()

    try:
        generation_result = generate_grounded_answer(generation_request)
    except Exception as error:
        if trace:
            trace.generation_ms = _elapsed_ms(generation_started_at)
            database_session.commit()

        _mark_trace_failed(
            database_session,
            trace.id if trace else None,
            total_started_at,
            error,
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to generate an answer",
        ) from error

    generation_ms = _elapsed_ms(generation_started_at)
    report_id: int | None = None

    try:
        if answer_input.save_report:
            report = Report(
                workspace_id=workspace_id,
                query=answer_input.query,
                answer=generation_result.answer,
                cited_chunk_ids=[
                    chunk.chunk_id for chunk in retrieved_chunks
                ],
                model_used=generation_result.model,
                retrieval_limit=answer_input.limit,
            )
            database_session.add(report)
            database_session.flush()
            report_id = report.id

        if trace:
            trace.report_id = report_id
            trace.status = "completed"
            trace.model_used = generation_result.model
            trace.openai_response_id = generation_result.response_id
            trace.input_tokens = generation_result.input_tokens
            trace.output_tokens = generation_result.output_tokens
            trace.total_tokens = generation_result.total_tokens
            trace.generation_ms = generation_ms
            trace.total_ms = _elapsed_ms(total_started_at)
            trace.completed_at = datetime.utcnow()
            trace.model_output = {
                "response_id": generation_result.response_id,
                "model": generation_result.model,
                "usage": {
                    "input_tokens": generation_result.input_tokens,
                    "output_tokens": generation_result.output_tokens,
                    "total_tokens": generation_result.total_tokens,
                },
                **(
                    {
                        "answer": generation_result.answer,
                        "output": generation_result.raw_output,
                    }
                    if trace.capture_content
                    else {"answer": "[content capture disabled]"}
                ),
            }

        database_session.commit()
    except Exception as error:
        _mark_trace_failed(
            database_session,
            trace.id if trace else None,
            total_started_at,
            error,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to save the answer result",
        ) from error

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
        trace_id=trace.id if trace else None,
        report_id=report_id,
        answer=generation_result.answer,
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


@router.get(
    "/workspaces/{workspace_id}/answer-traces",
    response_model=list[AnswerTraceSummaryResponse],
)
def list_answer_traces(
    workspace_id: int,
    database_session: Session = Depends(get_database_session),
):
    workspace = database_session.get(Workspace, workspace_id)

    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    return (
        database_session.query(AnswerTrace)
        .filter(AnswerTrace.workspace_id == workspace_id)
        .order_by(AnswerTrace.created_at.desc())
        .limit(100)
        .all()
    )


@router.get(
    "/answer-traces/{trace_id}",
    response_model=AnswerTraceDetailResponse,
)
def get_answer_trace(
    trace_id: str,
    database_session: Session = Depends(get_database_session),
):
    trace = database_session.get(AnswerTrace, trace_id)

    if trace is None:
        raise HTTPException(status_code=404, detail="Answer trace not found")

    return trace
