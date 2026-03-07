import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from bed.models.goal import GoalClass


class GoalCreate(BaseModel):
    description: str
    goal_class: GoalClass
    quantity: float | None = None
    value: float | None = None


class GoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    description: str
    goal_class: GoalClass
    quantity: float | None
    value: float | None
    created_at: datetime


class GoalUpdate(BaseModel):
    description: str | None = None
    goal_class: GoalClass | None = None
    quantity: float | None = None
    value: float | None = None
