import hashlib
import secrets
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.database import get_database_session
from app.models.workspace import Workspace

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    owner_id: str
    rate_limit_key: str


def _token_owner_id(token: str, settings: Settings) -> str:
    if len(settings.beta_access_tokens) == 1:
        return settings.beta_owner_id

    fingerprint = hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]
    return f"beta-{fingerprint}"


def require_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> Principal:
    client_host = request.client.host if request.client else "unknown"

    if settings.auth_mode == "disabled":
        return Principal(
            owner_id=settings.beta_owner_id,
            rate_limit_key=f"ip:{client_host}",
        )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A bearer access token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    matched_token = next(
        (
            configured_token
            for configured_token in settings.beta_access_tokens
            if secrets.compare_digest(
                credentials.credentials,
                configured_token,
            )
        ),
        None,
    )

    if matched_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    owner_id = _token_owner_id(matched_token, settings)
    return Principal(
        owner_id=owner_id,
        rate_limit_key=f"owner:{owner_id}",
    )


def get_owned_workspace(
    workspace_id: int,
    principal: Principal,
    database_session: Session,
) -> Workspace:
    workspace = (
        database_session.query(Workspace)
        .filter(
            Workspace.id == workspace_id,
            Workspace.owner_id == principal.owner_id,
        )
        .first()
    )

    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    return workspace


def require_owned_workspace(
    workspace_id: int,
    principal: Principal = Depends(require_principal),
    database_session: Session = Depends(get_database_session),
) -> Workspace:
    return get_owned_workspace(
        workspace_id=workspace_id,
        principal=principal,
        database_session=database_session,
    )
