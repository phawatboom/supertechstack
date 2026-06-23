from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.db.database import Base, get_database_session
from app.models.workspace import Workspace
from app.security import Principal, _verify_supabase_token, require_principal


def make_settings(**overrides) -> Settings:
    values = {
        "environment": "test",
        "database_url": "sqlite+pysqlite:///:memory:",
        "allowed_origins": ("http://localhost:3000",),
        "auth_mode": "supabase",
        "beta_access_tokens": (),
        "beta_owner_id": "beta-user",
        "supabase_url": "https://example.supabase.co",
        "supabase_jwt_audience": "authenticated",
        "demo_enabled": False,
        "demo_owner_id": "public-demo",
        "demo_embedding_requests": 3,
        "demo_answer_requests": 1,
        "demo_window_seconds": 86_400,
        "demo_max_output_tokens": 500,
        "demo_max_retrieval_limit": 5,
        "demo_max_query_chars": 1_000,
        "max_upload_size_bytes": 1024,
        "allowed_answer_models": ("test-model",),
        "default_answer_model": "test-model",
        "default_max_output_tokens": 100,
        "max_output_tokens": 200,
        "max_retrieval_limit": 10,
        "rate_limit_requests": 60,
        "rate_limit_window_seconds": 60,
        "observability_enabled": False,
        "observability_capture_content": False,
    }
    values.update(overrides)
    return Settings(**values)


def make_client(settings: Settings) -> TestClient:
    app = FastAPI()
    app.dependency_overrides[get_settings] = lambda: settings

    @app.get("/protected")
    def protected(
        principal: Principal = Depends(require_principal),
    ):
        return {"owner_id": principal.owner_id}

    return TestClient(app)


def test_supabase_auth_requires_bearer_token():
    response = make_client(make_settings()).get("/protected")

    assert response.status_code == 401
    assert response.json()["detail"] == "A bearer access token is required"


def test_supabase_auth_uses_verified_subject_as_owner(monkeypatch):
    monkeypatch.setattr(
        "app.security._verify_supabase_token",
        lambda token, settings: "user-123",
    )

    response = make_client(make_settings()).get(
        "/protected",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"owner_id": "user-123"}


def test_beta_auth_still_supports_existing_deployments():
    settings = make_settings(
        auth_mode="beta",
        beta_access_tokens=("shared-beta-token",),
    )

    response = make_client(settings).get(
        "/protected",
        headers={"Authorization": "Bearer shared-beta-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"owner_id": "beta-user"}


def test_supabase_verifier_checks_signed_claims(monkeypatch):
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()

    class SigningKey:
        key = public_key

    class JwksClient:
        def get_signing_key_from_jwt(self, token):
            return SigningKey()

    monkeypatch.setattr(
        "app.security._jwks_client",
        lambda supabase_url: JwksClient(),
    )

    settings = make_settings()
    token = jwt.encode(
        {
            "sub": "verified-user",
            "aud": "authenticated",
            "iss": "https://example.supabase.co/auth/v1",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    assert _verify_supabase_token(token, settings) == "verified-user"


def test_public_demo_allows_only_allowlisted_workspace_routes():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        workspace = Workspace(owner_id="public-demo", name="Demo")
        session.add(workspace)
        session.commit()
        workspace_id = workspace.id

    settings = make_settings(demo_enabled=True)
    app = FastAPI()
    app.dependency_overrides[get_settings] = lambda: settings

    def database_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_database_session] = database_override

    @app.get("/workspaces/{workspace_id}")
    def read_demo(
        workspace_id: int,
        principal: Principal = Depends(require_principal),
    ):
        return {"is_demo": principal.is_demo}

    @app.post("/workspaces/{workspace_id}/sources")
    def write_demo(
        workspace_id: int,
        principal: Principal = Depends(require_principal),
    ):
        return {"is_demo": principal.is_demo}

    client = TestClient(app)

    read_response = client.get(f"/workspaces/{workspace_id}")
    write_response = client.post(f"/workspaces/{workspace_id}/sources")

    assert read_response.status_code == 200
    assert read_response.json() == {"is_demo": True}
    assert write_response.status_code == 401
