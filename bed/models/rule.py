import uuid

from sqlalchemy import JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid, DateTime

from bed.database import Base


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    current: Mapped[bool] = mapped_column(default=True, nullable=False)
    target: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=2), nullable=True)
    min: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=2), nullable=True)
    max: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=2), nullable=True)
    asset_class: Mapped[str | None] = mapped_column(String(255), nullable=True)
    asset_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
