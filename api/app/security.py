import hashlib
import logging
import re
import secrets
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.database import get_database_session
from app.models.workspace import Workspace

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Principal:
    owner_id: str
    rate_limit_key: str
    is_demo: bool = False


def _token_owner_id(token: str, settings: Settings) -> str:
    if len(settings.beta_access_tokens) == 1:
        return settings.beta_owner_id

    fingerprint = hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]
    return f"beta-{fingerprint}"


@lru_cache
def _jwks_client(supabase_url: str) -> PyJWKClient:
    return PyJWKClient(
        f"{supabase_url}/auth/v1/.well-known/jwks.json",
        cache_jwk_set=True,
        lifespan=600,
    )


def _verify_supabase_token(token: str, settings: Settings) -> str:
    try:
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg")

        if algorithm not in {"RS256", "ES256"}:
            raise PyJWTError("Unsupported JWT signing algorithm")

        signing_key = _jwks_client(settings.supabase_url).get_signing_key_from_jwt(
            token
        )
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[algorithm],
            audience=settings.supabase_jwt_audience,
            issuer=f"{settings.supabase_url}/auth/v1",
            options={"require": ["exp", "iss", "sub"]},
        )
        owner_id = claims.get("sub")

        if not isinstance(owner_id, str) or not owner_id:
            raise PyJWTError("JWT subject is missing")

        return owner_id
    except PyJWTError as error:
        if not settings.is_production:
            logger.warning(
                "Supabase JWT validation failed: %s: %s",
                type(error).__name__,
                error,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


DEMO_WORKSPACE_PATH = re.compile(
    r"^/workspaces/(?P<workspace_id>\d+)(?P<action>/sources|/chunks|/search|/answer)?$"
)


def _demo_workspace_id_for_request(request: Request) -> int | None:
    match = DEMO_WORKSPACE_PATH.fullmatch(request.url.path)

    if match is None:
        return None

    action = match.group("action") or ""
    allowed = (
        (request.method == "GET" and action in {"", "/sources", "/chunks"})
        or (
            request.method == "POST"
            and action in {"/search", "/answer"}
        )
    )

    return int(match.group("workspace_id")) if allowed else None


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")

    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()

    return request.client.host if request.client else "unknown"


def require_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
    database_session: Session = Depends(get_database_session),
) -> Principal:
    client_host = _client_ip(request)

    if settings.auth_mode == "disabled":
        return Principal(
            owner_id=settings.beta_owner_id,
            rate_limit_key=f"ip:{client_host}",
        )

    demo_workspace_id = (
        _demo_workspace_id_for_request(request)
        if settings.demo_enabled
        else None
    )

    if demo_workspace_id is not None:
        demo_workspace = (
            database_session.query(Workspace.id)
            .filter(
                Workspace.id == demo_workspace_id,
                Workspace.owner_id == settings.demo_owner_id,
            )
            .first()
        )

        if demo_workspace is not None:
            return Principal(
                owner_id=settings.demo_owner_id,
                rate_limit_key=f"demo-ip:{client_host}",
                is_demo=True,
            )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A bearer access token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if settings.auth_mode == "supabase":
        owner_id = _verify_supabase_token(
            credentials.credentials,
            settings,
        )
        return Principal(
            owner_id=owner_id,
            rate_limit_key=f"owner:{owner_id}",
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
