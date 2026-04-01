import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RuleBase(BaseModel):
    description: str
    current: bool = True
    target: float | None = None
    min: float | None = None
    max: float | None = None
    asset_class: str | None = None
    asset_type: str | None = None
    category: str | None = None
    subcategory: str | None = None
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_target_bounds(self):
        if self.target is not None and (self.min is not None or self.max is not None):
            raise ValueError("target cannot be combined with min or max")
        return self


class RuleCreate(RuleBase):
    pass


class RuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    description: str
    current: bool
    target: float | None
    min: float | None
    max: float | None
    asset_class: str | None
    asset_type: str | None
    category: str | None
    subcategory: str | None
    tags: list[str]
    created_at: datetime


class RuleUpdate(BaseModel):
    description: str | None = None
    current: bool | None = None
    target: float | None = None
    min: float | None = None
    max: float | None = None
    asset_class: str | None = None
    asset_type: str | None = None
    category: str | None = None
    subcategory: str | None = None
    tags: list[str] | None = None

    @model_validator(mode="after")
    def validate_target_bounds(self):
        if self.target is not None and (self.min is not None or self.max is not None):
            raise ValueError("target cannot be combined with min or max")
        return self
