import enum
import uuid

from sqlalchemy import Enum, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid, DateTime

from bed.database import Base


class GoalClass(str, enum.Enum):
    quantity = "quantity"
    invested_value = "invested-value"
    current_value = "current-value"


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    goal_class: Mapped[GoalClass] = mapped_column(Enum(GoalClass), nullable=False)
    quantity: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=8), nullable=True)
    value: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=2), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
