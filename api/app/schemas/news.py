from datetime import datetime
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

NewsFrequency = Literal["manual", "daily"]


def canonicalize_news_url(value: str) -> str:
    parsed_url = urlsplit(value.strip())
    scheme = parsed_url.scheme.lower()
    hostname = parsed_url.hostname.lower() if parsed_url.hostname else ""

    if not scheme or not hostname:
        raise ValueError("URL must include a scheme and hostname")

    if scheme not in {"http", "https"}:
        raise ValueError("URL must use http or https")

    netloc = hostname

    if parsed_url.port:
        is_default_port = (
            (scheme == "http" and parsed_url.port == 80)
            or (scheme == "https" and parsed_url.port == 443)
        )
        if not is_default_port:
            netloc = f"{netloc}:{parsed_url.port}"

    query_params = [
        (key, value)
        for key, value in parse_qsl(parsed_url.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
    ]
    query = urlencode(sorted(query_params), doseq=True)
    path = parsed_url.path or "/"

    return urlunsplit((scheme, netloc, path, query, ""))


class NewsSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    url: str = Field(min_length=1, max_length=2_000)
    canonical_url: str = Field(min_length=1, max_length=2_000)
    snippet: str | None = Field(default=None, max_length=2_000)
    publisher: str | None = Field(default=None, max_length=255)
    published_at: datetime | None = None
    provider: str = Field(min_length=1, max_length=100)
    external_id: str | None = Field(default=None, max_length=255)

    @field_validator("title", "url", "canonical_url", "provider")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Value cannot be blank")

        return value

    @field_validator("snippet", "publisher", "external_id")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None

    @field_validator("url", "canonical_url")
    @classmethod
    def validate_http_url(cls, value: str) -> str:
        return canonicalize_news_url(value)


class NewsSearchConfigCreate(BaseModel):
    query: str = Field(min_length=3, max_length=2_000)
    is_enabled: bool = False
    frequency: NewsFrequency = "manual"
    run_at: str | None = Field(
        default=None,
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
    )
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    max_results_per_run: int = Field(default=10, ge=1, le=50)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Value cannot be blank")

        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        value = value.strip()

        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Timezone must be a valid IANA timezone") from error

        return value

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.frequency == "daily" and self.run_at is None:
            raise ValueError("run_at is required for daily monitoring")

        return self


class NewsSearchConfigUpdate(BaseModel):
    query: str | None = Field(default=None, min_length=3, max_length=2_000)
    is_enabled: bool | None = None
    frequency: NewsFrequency | None = None
    run_at: str | None = Field(
        default=None,
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
    )
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    max_results_per_run: int | None = Field(default=None, ge=1, le=50)

    @field_validator("query")
    @classmethod
    def strip_optional_query(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Value cannot be blank")

        return value

    @field_validator("timezone")
    @classmethod
    def validate_optional_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Timezone must be a valid IANA timezone") from error

        return value

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        return self


class NewsSearchConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    query: str
    is_enabled: bool
    frequency: NewsFrequency
    run_at: str | None
    timezone: str
    max_results_per_run: int
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class NewsRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    query_used: str
    status: str
    articles_found: int
    articles_processed: int
    insights_created: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
