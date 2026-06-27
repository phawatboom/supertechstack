from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

NewsFrequency = Literal["manual", "daily"]


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
