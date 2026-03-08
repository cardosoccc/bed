import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from bed.models.asset import AssetClass, AssetType


class AssetCreate(BaseModel):
    name: str
    description: str | None = None
    asset_class: AssetClass
    asset_type: AssetType
    quantity: float = 0
    initial_value: float = 0
    current_value: float = 0
    category: str | None = None
    subcategory: str | None = None
    tags: list[str] = []


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    asset_class: AssetClass
    asset_type: AssetType
    quantity: float
    initial_value: float
    current_value: float
    category: str | None
    subcategory: str | None
    tags: list[str]
    created_at: datetime


class AssetUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    asset_class: AssetClass | None = None
    asset_type: AssetType | None = None
    quantity: float | None = None
    initial_value: float | None = None
    current_value: float | None = None
    category: str | None = None
    subcategory: str | None = None
    tags: list[str] | None = None
