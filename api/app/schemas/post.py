from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PostStatus = Literal["draft", "published", "archived"]
PostVisibility = Literal["private", "workspace", "public"]


class CreatePostFromSourceRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    excerpt: str | None = Field(default=None, max_length=1_000)
    cover_image_url: str | None = Field(default=None, max_length=2_000)
    visibility: PostVisibility = "private"

    @field_validator("title", "excerpt", "cover_image_url")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    markdown_content: str | None = Field(default=None, min_length=1)
    excerpt: str | None = Field(default=None, max_length=1_000)
    cover_image_url: str | None = Field(default=None, max_length=2_000)
    visibility: PostVisibility | None = None
    status: PostStatus | None = None

    @field_validator("title", "markdown_content", "excerpt", "cover_image_url")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        return self


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    source_id: int | None
    author_id: str
    title: str
    slug: str
    markdown_content: str
    excerpt: str | None
    cover_image_url: str | None
    visibility: PostVisibility
    status: PostStatus
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
