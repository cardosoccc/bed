import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RuleCreate(BaseModel):
    description: str
    invested_value: float | None = None
    current_value: float | None = None
    asset_class: str | None = None
    asset_type: str | None = None
    category: str | None = None
    subcategory: str | None = None
    tags: list[str] = []


class RuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    description: str
    invested_value: float | None
    current_value: float | None
    asset_class: str | None
    asset_type: str | None
    category: str | None
    subcategory: str | None
    tags: list[str]
    created_at: datetime


class RuleUpdate(BaseModel):
    description: str | None = None
    invested_value: float | None = None
    current_value: float | None = None
    asset_class: str | None = None
    asset_type: str | None = None
    category: str | None = None
    subcategory: str | None = None
    tags: list[str] | None = None
