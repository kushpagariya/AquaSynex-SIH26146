"""Common schemas including canonical envelope, metadata, and pagination."""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, Generic, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field, model_validator


def to_camel(snake_str: str) -> str:
    """Convert snake_case string to camelCase."""
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class CamelModel(BaseModel):
    """Base Pydantic model with automatic camelCase alias generator and UTC ISO serialization."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class PaginationMeta(CamelModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ApiMeta(CamelModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pagination: Optional[PaginationMeta] = None


class ApiError(CamelModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


T = TypeVar("T")


class ApiResponse(CamelModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[ApiError] = None
    meta: ApiMeta = Field(default_factory=ApiMeta)

    @model_validator(mode="after")
    def validate_envelope(self) -> "ApiResponse[T]":
        if self.success and self.error is not None:
            raise ValueError("Successful response must not contain an error")
        if not self.success and self.error is None:
            raise ValueError("Failed response must contain an error")
        return self
