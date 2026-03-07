import uuid

import pytest

from bed.models.goal import GoalClass
from bed.schemas.goal import GoalCreate, GoalUpdate
from bed.services import goals as service


@pytest.mark.asyncio
async def test_create_goal(db_session):
    data = GoalCreate(
        description="Retirement",
        goal_class=GoalClass.current_value,
        value=1000000,
    )
    goal = await service.create_goal(db_session, data)
    assert goal.description == "Retirement"
    assert goal.goal_class == GoalClass.current_value
    assert goal.value == 1000000
    assert goal.id is not None


@pytest.mark.asyncio
async def test_list_goals(db_session):
    for desc in ["Emergency", "Retirement", "Vacation"]:
        await service.create_goal(db_session, GoalCreate(
            description=desc, goal_class=GoalClass.invested_value
        ))
    goals = await service.list_goals(db_session)
    assert len(goals) == 3
    assert [g.description for g in goals] == ["Emergency", "Retirement", "Vacation"]


@pytest.mark.asyncio
async def test_get_goal(db_session):
    created = await service.create_goal(db_session, GoalCreate(
        description="House", goal_class=GoalClass.invested_value, value=500000
    ))
    fetched = await service.get_goal(db_session, created.id)
    assert fetched is not None
    assert fetched.description == "House"


@pytest.mark.asyncio
async def test_get_goal_not_found(db_session):
    result = await service.get_goal(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_update_goal(db_session):
    created = await service.create_goal(db_session, GoalCreate(
        description="Car", goal_class=GoalClass.invested_value, value=50000
    ))
    updated = await service.update_goal(db_session, created.id, GoalUpdate(value=60000))
    assert updated is not None
    assert updated.value == 60000
    assert updated.description == "Car"


@pytest.mark.asyncio
async def test_update_goal_not_found(db_session):
    result = await service.update_goal(db_session, uuid.uuid4(), GoalUpdate(description="X"))
    assert result is None


@pytest.mark.asyncio
async def test_delete_goal(db_session):
    created = await service.create_goal(db_session, GoalCreate(
        description="Delete me", goal_class=GoalClass.quantity, quantity=100
    ))
    assert await service.delete_goal(db_session, created.id) is True
    assert await service.get_goal(db_session, created.id) is None


@pytest.mark.asyncio
async def test_delete_goal_not_found(db_session):
    assert await service.delete_goal(db_session, uuid.uuid4()) is False
