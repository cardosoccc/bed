import uuid
from datetime import date as date_type

from sqlalchemy import Date, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime, Uuid

from bed.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    product: Mapped[str] = mapped_column(String(500), nullable=False)
    ticker: Mapped[str | None] = mapped_column(String(50), nullable=True)
    institution: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(precision=18, scale=8), nullable=False, default=0)
    unit_value: Mapped[float] = mapped_column(Numeric(precision=18, scale=8), nullable=False, default=0)
    total_value: Mapped[float] = mapped_column(Numeric(precision=18, scale=2), nullable=False, default=0)
    row_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
