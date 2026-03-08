import enum
import uuid

from sqlalchemy import Enum, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid, DateTime

from bed.database import Base


class AssetClass(str, enum.Enum):
    equity = "equity"
    fixed_income = "fixed-income"


class AssetType(str, enum.Enum):
    stock = "stock"
    bond = "bond"
    fund = "fund"
    etf = "etf"
    reit = "reit"
    crypto = "crypto"
    other = "other"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    asset_class: Mapped[AssetClass] = mapped_column(Enum(AssetClass), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(precision=18, scale=8), nullable=False, default=0)
    initial_value: Mapped[float] = mapped_column(Numeric(precision=18, scale=2), nullable=False, default=0)
    current_value: Mapped[float] = mapped_column(Numeric(precision=18, scale=2), nullable=False, default=0)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
