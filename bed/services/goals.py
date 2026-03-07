import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bed.models.goal import Goal
from bed.schemas.goal import GoalCreate, GoalUpdate


async def list_goals(db: AsyncSession) -> list[Goal]:
    result = await db.execute(select(Goal).order_by(Goal.description))
    return list(result.scalars().all())


async def get_goal(db: AsyncSession, goal_id: uuid.UUID) -> Goal | None:
    return await db.get(Goal, goal_id)


async def create_goal(db: AsyncSession, data: GoalCreate) -> Goal:
    goal = Goal(**data.model_dump())
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal


async def update_goal(db: AsyncSession, goal_id: uuid.UUID, data: GoalUpdate) -> Goal | None:
    goal = await db.get(Goal, goal_id)
    if not goal:
        return None
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(goal, key, value)
    await db.commit()
    await db.refresh(goal)
    return goal


async def delete_goal(db: AsyncSession, goal_id: uuid.UUID) -> bool:
    goal = await db.get(Goal, goal_id)
    if not goal:
        return False
    await db.delete(goal)
    await db.commit()
    return True
