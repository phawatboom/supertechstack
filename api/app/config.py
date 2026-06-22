import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

API_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = (
    API_DIR.parent.parent
    if API_DIR.parent.name == "apps"
    else None
)

if REPOSITORY_ROOT is not None:
    load_dotenv(REPOSITORY_ROOT / ".env")

load_dotenv(API_DIR / ".env", override=True)


def _csv(name: str, default: str) -> tuple[str, ...]:
    return tuple(
        value.strip()
        for value in os.getenv(name, default).split(",")
        if value.strip()
    )

def _integer(name: str, default: int, minimum: int = 1) -> int:
    raw_value = os.getenv(name, str(default))

    try:
        value = int(raw_value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be an integer") from error

    if value < minimum:
        raise RuntimeError(f"{name} must be at least {minimum}")

    return value


def _boolean(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    environment: str
    database_url: str
    allowed_origins: tuple[str, ...]
    auth_mode: str
    beta_access_tokens: tuple[str, ...]
    beta_owner_id: str
    max_upload_size_bytes: int
    allowed_answer_models: tuple[str, ...]
    default_answer_model: str
    default_max_output_tokens: int
    max_output_tokens: int
    max_retrieval_limit: int
    rate_limit_requests: int
    rate_limit_window_seconds: int
    observability_enabled: bool
    observability_capture_content: bool

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    database_url = os.getenv("DATABASE_URL", "").strip()

    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    auth_mode = os.getenv(
        "AUTH_MODE",
        "beta" if environment == "production" else "disabled",
    ).strip().lower()

    if auth_mode not in {"disabled", "beta"}:
        raise RuntimeError("AUTH_MODE must be either 'disabled' or 'beta'")

    beta_access_tokens = _csv("BETA_ACCESS_TOKENS", "")

    if environment == "production" and auth_mode == "disabled":
        raise RuntimeError("AUTH_MODE=disabled is not allowed in production")

    if auth_mode == "beta" and not beta_access_tokens:
        raise RuntimeError(
            "BETA_ACCESS_TOKENS must contain at least one token "
            "when AUTH_MODE=beta"
        )

    allowed_answer_models = _csv(
        "ALLOWED_OPENAI_ANSWER_MODELS",
        "gpt-5.4-mini",
    )
    default_answer_model = os.getenv(
        "OPENAI_ANSWER_MODEL",
        allowed_answer_models[0],
    ).strip()

    if default_answer_model not in allowed_answer_models:
        raise RuntimeError(
            "OPENAI_ANSWER_MODEL must be included in "
            "ALLOWED_OPENAI_ANSWER_MODELS"
        )

    max_output_tokens = _integer("MAX_OUTPUT_TOKENS", 4_000)
    default_max_output_tokens = _integer(
        "DEFAULT_MAX_OUTPUT_TOKENS",
        min(2_000, max_output_tokens),
    )

    if default_max_output_tokens > max_output_tokens:
        raise RuntimeError(
            "DEFAULT_MAX_OUTPUT_TOKENS cannot exceed MAX_OUTPUT_TOKENS"
        )

    return Settings(
        environment=environment,
        database_url=database_url,
        allowed_origins=_csv(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        ),
        auth_mode=auth_mode,
        beta_access_tokens=beta_access_tokens,
        beta_owner_id=os.getenv("BETA_OWNER_ID", "beta-user").strip(),
        max_upload_size_bytes=_integer(
            "MAX_UPLOAD_SIZE_BYTES",
            60 * 1024 * 1024,
        ),
        allowed_answer_models=allowed_answer_models,
        default_answer_model=default_answer_model,
        default_max_output_tokens=default_max_output_tokens,
        max_output_tokens=max_output_tokens,
        max_retrieval_limit=_integer("MAX_RETRIEVAL_LIMIT", 20),
        rate_limit_requests=_integer("RATE_LIMIT_REQUESTS", 60),
        rate_limit_window_seconds=_integer(
            "RATE_LIMIT_WINDOW_SECONDS",
            60,
        ),
        observability_enabled=_boolean("OBSERVABILITY_ENABLED", True),
        observability_capture_content=_boolean(
            "OBSERVABILITY_CAPTURE_CONTENT",
            environment != "production",
        ),
    )
