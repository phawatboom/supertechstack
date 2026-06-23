import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.models.workspace import Workspace
from app.routes.workspaces import create_workspace
from app.schemas.workspace import WorkspaceCreate
from app.security import Principal, get_owned_workspace


@pytest.fixture
def database_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


def test_owner_can_access_workspace(database_session: Session):
    workspace = Workspace(owner_id="user-a", name="Private workspace")
    database_session.add(workspace)
    database_session.commit()

    result = get_owned_workspace(
        workspace.id,
        Principal(owner_id="user-a", rate_limit_key="owner:user-a"),
        database_session,
    )

    assert result.id == workspace.id


def test_other_user_cannot_access_workspace(database_session: Session):
    workspace = Workspace(owner_id="user-a", name="Private workspace")
    database_session.add(workspace)
    database_session.commit()

    with pytest.raises(HTTPException) as error:
        get_owned_workspace(
            workspace.id,
            Principal(owner_id="user-b", rate_limit_key="owner:user-b"),
            database_session,
        )

    assert error.value.status_code == 404


def test_workspace_creation_is_idempotent(database_session: Session):
    principal = Principal(
        owner_id="user-a",
        rate_limit_key="owner:user-a",
    )
    workspace_input = WorkspaceCreate(
        name="Research",
        description="Test description",
    )

    first = create_workspace(
        workspace_input,
        principal,
        database_session,
        idempotency_key="request-123",
    )
    second = create_workspace(
        workspace_input,
        principal,
        database_session,
        idempotency_key="request-123",
    )

    assert first.id == second.id
    assert database_session.query(Workspace).count() == 1


def test_creation_key_is_scoped_to_owner(database_session: Session):
    workspace_input = WorkspaceCreate(name="Research")

    first = create_workspace(
        workspace_input,
        Principal(owner_id="user-a", rate_limit_key="owner:user-a"),
        database_session,
        idempotency_key="request-123",
    )
    second = create_workspace(
        workspace_input,
        Principal(owner_id="user-b", rate_limit_key="owner:user-b"),
        database_session,
        idempotency_key="request-123",
    )

    assert first.id != second.id
    assert database_session.query(Workspace).count() == 2
