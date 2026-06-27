from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import get_database_session
from app.models.news import NewsRun, NewsSearchConfig
from app.rate_limit import enforce_rate_limit
from app.schemas.news import (
    NewsRunResponse,
    NewsSearchConfigCreate,
    NewsSearchConfigResponse,
    NewsSearchConfigUpdate,
)
from app.security import Principal, get_owned_workspace

router = APIRouter(tags=["news"])


def _get_news_config(
    workspace_id: int,
    database_session: Session,
) -> NewsSearchConfig:
    config = (
        database_session.query(NewsSearchConfig)
        .filter(NewsSearchConfig.workspace_id == workspace_id)
        .first()
    )

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="News monitoring is not configured for this workspace",
        )

    return config


@router.post(
    "/workspaces/{workspace_id}/news-config",
    response_model=NewsSearchConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_news_config(
    workspace_id: int,
    config_input: NewsSearchConfigCreate,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    get_owned_workspace(workspace_id, principal, database_session)

    existing_config = (
        database_session.query(NewsSearchConfig.id)
        .filter(NewsSearchConfig.workspace_id == workspace_id)
        .first()
    )

    if existing_config is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="News monitoring is already configured for this workspace",
        )

    config = NewsSearchConfig(
        workspace_id=workspace_id,
        **config_input.model_dump(),
    )
    database_session.add(config)
    try:
        database_session.commit()
    except IntegrityError as error:
        database_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="News monitoring is already configured for this workspace",
        ) from error

    database_session.refresh(config)

    return config


@router.get(
    "/workspaces/{workspace_id}/news-config",
    response_model=NewsSearchConfigResponse,
)
def get_news_config(
    workspace_id: int,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    get_owned_workspace(workspace_id, principal, database_session)
    return _get_news_config(workspace_id, database_session)


@router.patch(
    "/workspaces/{workspace_id}/news-config",
    response_model=NewsSearchConfigResponse,
)
def update_news_config(
    workspace_id: int,
    config_input: NewsSearchConfigUpdate,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    get_owned_workspace(workspace_id, principal, database_session)
    config = _get_news_config(workspace_id, database_session)
    changes = config_input.model_dump(exclude_unset=True)

    next_frequency = changes.get("frequency", config.frequency)
    next_run_at = changes.get("run_at", config.run_at)

    if next_frequency == "daily" and next_run_at is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="run_at is required for daily monitoring",
        )

    for field, value in changes.items():
        setattr(config, field, value)

    database_session.commit()
    database_session.refresh(config)

    return config


@router.get(
    "/workspaces/{workspace_id}/news/runs",
    response_model=list[NewsRunResponse],
)
def list_news_runs(
    workspace_id: int,
    principal: Principal = Depends(enforce_rate_limit),
    database_session: Session = Depends(get_database_session),
):
    get_owned_workspace(workspace_id, principal, database_session)
    return (
        database_session.query(NewsRun)
        .filter(NewsRun.workspace_id == workspace_id)
        .order_by(NewsRun.created_at.desc())
        .all()
    )
