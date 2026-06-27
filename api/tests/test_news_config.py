from datetime import datetime

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.models.news import NewsRun, NewsSearchConfig
from app.models.workspace import Workspace
from app.routes.news import (
    create_news_config,
    get_news_config,
    list_news_runs,
    update_news_config,
)
from app.schemas.news import NewsSearchConfigCreate, NewsSearchConfigUpdate
from app.security import Principal


@pytest.fixture
def database_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


def create_workspace(
    database_session: Session,
    owner_id: str = "user-a",
) -> Workspace:
    workspace = Workspace(
        owner_id=owner_id,
        name="News research",
    )
    database_session.add(workspace)
    database_session.commit()
    database_session.refresh(workspace)
    return workspace


def principal(owner_id: str = "user-a") -> Principal:
    return Principal(
        owner_id=owner_id,
        rate_limit_key=f"owner:{owner_id}",
    )


def test_owner_can_create_and_read_news_config(database_session: Session):
    workspace = create_workspace(database_session)

    created = create_news_config(
        workspace_id=workspace.id,
        config_input=NewsSearchConfigCreate(
            query="New Zealand banking regulation",
        ),
        principal=principal(),
        database_session=database_session,
    )
    loaded = get_news_config(
        workspace_id=workspace.id,
        principal=principal(),
        database_session=database_session,
    )

    assert created.id == loaded.id
    assert loaded.workspace_id == workspace.id
    assert loaded.frequency == "manual"
    assert loaded.max_results_per_run == 10


def test_duplicate_news_config_is_rejected(database_session: Session):
    workspace = create_workspace(database_session)
    config_input = NewsSearchConfigCreate(query="AI infrastructure")

    create_news_config(
        workspace_id=workspace.id,
        config_input=config_input,
        principal=principal(),
        database_session=database_session,
    )

    with pytest.raises(HTTPException) as error:
        create_news_config(
            workspace_id=workspace.id,
            config_input=config_input,
            principal=principal(),
            database_session=database_session,
        )

    assert error.value.status_code == 409
    assert database_session.query(NewsSearchConfig).count() == 1


def test_missing_news_config_returns_not_found(database_session: Session):
    workspace = create_workspace(database_session)

    with pytest.raises(HTTPException) as error:
        get_news_config(
            workspace_id=workspace.id,
            principal=principal(),
            database_session=database_session,
        )

    assert error.value.status_code == 404


def test_other_user_cannot_access_news_config(database_session: Session):
    workspace = create_workspace(database_session, owner_id="user-a")

    with pytest.raises(HTTPException) as error:
        create_news_config(
            workspace_id=workspace.id,
            config_input=NewsSearchConfigCreate(query="Private topic"),
            principal=principal("user-b"),
            database_session=database_session,
        )

    assert error.value.status_code == 404


def test_daily_config_requires_run_time():
    with pytest.raises(ValidationError):
        NewsSearchConfigCreate(
            query="Daily AI news",
            frequency="daily",
            timezone="Asia/Bangkok",
        )


def test_invalid_timezone_is_rejected():
    with pytest.raises(ValidationError):
        NewsSearchConfigCreate(
            query="Daily AI news",
            frequency="daily",
            run_at="09:00",
            timezone="Not/A_Timezone",
        )


def test_config_can_be_updated_to_daily(database_session: Session):
    workspace = create_workspace(database_session)
    create_news_config(
        workspace_id=workspace.id,
        config_input=NewsSearchConfigCreate(query="AI infrastructure"),
        principal=principal(),
        database_session=database_session,
    )

    updated = update_news_config(
        workspace_id=workspace.id,
        config_input=NewsSearchConfigUpdate(
            frequency="daily",
            run_at="09:30",
            timezone="Asia/Bangkok",
            is_enabled=True,
            max_results_per_run=15,
        ),
        principal=principal(),
        database_session=database_session,
    )

    assert updated.frequency == "daily"
    assert updated.run_at == "09:30"
    assert updated.timezone == "Asia/Bangkok"
    assert updated.is_enabled is True
    assert updated.max_results_per_run == 15


def test_daily_update_without_run_time_is_rejected(
    database_session: Session,
):
    workspace = create_workspace(database_session)
    create_news_config(
        workspace_id=workspace.id,
        config_input=NewsSearchConfigCreate(query="AI infrastructure"),
        principal=principal(),
        database_session=database_session,
    )

    with pytest.raises(HTTPException) as error:
        update_news_config(
            workspace_id=workspace.id,
            config_input=NewsSearchConfigUpdate(frequency="daily"),
            principal=principal(),
            database_session=database_session,
        )

    assert error.value.status_code == 422


def test_news_runs_are_scoped_to_workspace_owner(
    database_session: Session,
):
    workspace = create_workspace(database_session)
    run = NewsRun(
        workspace_id=workspace.id,
        query_used="AI infrastructure",
        status="completed",
        articles_found=5,
        articles_processed=4,
        insights_created=3,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    database_session.add(run)
    database_session.commit()

    runs = list_news_runs(
        workspace_id=workspace.id,
        principal=principal(),
        database_session=database_session,
    )

    assert [item.id for item in runs] == [run.id]

    with pytest.raises(HTTPException) as error:
        list_news_runs(
            workspace_id=workspace.id,
            principal=principal("user-b"),
            database_session=database_session,
        )

    assert error.value.status_code == 404
