import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.models.workspace import Workspace
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
