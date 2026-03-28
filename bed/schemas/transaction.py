import uuid
from datetime import date as date_type
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TransactionCreate(BaseModel):
    date: date_type
    type: str
    product: str
    ticker: Optional[str] = None
    institution: str
    quantity: float = 0
    unit_value: float = 0
    total_value: float = 0
    row_hash: Optional[str] = None
    tags: list[str] = []


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    date: date_type
    type: str
    product: str
    ticker: Optional[str]
    institution: str
    quantity: float
    unit_value: float
    total_value: float
    row_hash: Optional[str]
    tags: list[str]
    created_at: datetime


class TransactionUpdate(BaseModel):
    date: Optional[date_type] = None
    type: Optional[str] = None
    product: Optional[str] = None
    ticker: Optional[str] = None
    institution: Optional[str] = None
    quantity: Optional[float] = None
    unit_value: Optional[float] = None
    total_value: Optional[float] = None
    tags: Optional[list[str]] = None
