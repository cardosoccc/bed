import uuid

import pytest
from pydantic import ValidationError

from bed.schemas.rule import RuleCreate, RuleUpdate
from bed.services import rules as service


@pytest.mark.asyncio
async def test_create_rule(db_session):
    data = RuleCreate(
        description="Max 30% equity",
        target=0.30,
        asset_class="equity",
    )
    rule = await service.create_rule(db_session, data)
    assert rule.description == "Max 30% equity"
    assert float(rule.target) == 0.30
    assert rule.current is True
    assert rule.asset_class == "equity"
    assert rule.id is not None


@pytest.mark.asyncio
async def test_list_rules(db_session):
    for desc in ["Rule A", "Rule B", "Rule C"]:
        await service.create_rule(db_session, RuleCreate(description=desc))
    rules = await service.list_rules(db_session)
    assert len(rules) == 3
    assert [r.description for r in rules] == ["Rule A", "Rule B", "Rule C"]


@pytest.mark.asyncio
async def test_get_rule(db_session):
    created = await service.create_rule(db_session, RuleCreate(
        description="Test Rule", target=50000, current=False
    ))
    fetched = await service.get_rule(db_session, created.id)
    assert fetched is not None
    assert fetched.description == "Test Rule"


@pytest.mark.asyncio
async def test_get_rule_not_found(db_session):
    result = await service.get_rule(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_update_rule(db_session):
    created = await service.create_rule(db_session, RuleCreate(
        description="Editable Rule", target=20
    ))
    updated = await service.update_rule(db_session, created.id, RuleUpdate(
        target=25, tags=["important"]
    ))
    assert updated is not None
    assert float(updated.target) == 25
    assert updated.tags == ["important"]
    assert updated.description == "Editable Rule"


@pytest.mark.asyncio
async def test_update_rule_not_found(db_session):
    result = await service.update_rule(db_session, uuid.uuid4(), RuleUpdate(description="X"))
    assert result is None


@pytest.mark.asyncio
async def test_delete_rule(db_session):
    created = await service.create_rule(db_session, RuleCreate(description="To Delete"))
    assert await service.delete_rule(db_session, created.id) is True
    assert await service.get_rule(db_session, created.id) is None


@pytest.mark.asyncio
async def test_delete_rule_not_found(db_session):
    assert await service.delete_rule(db_session, uuid.uuid4()) is False


@pytest.mark.asyncio
async def test_create_rule_with_percentage_target(db_session):
    data = RuleCreate(
        description="30% equity",
        target=0.30,
        asset_class="equity",
    )
    rule = await service.create_rule(db_session, data)
    assert rule.description == "30% equity"
    assert float(rule.target) == 0.30
    assert rule.asset_class == "equity"


@pytest.mark.asyncio
async def test_update_rule_target(db_session):
    created = await service.create_rule(db_session, RuleCreate(
        description="Target Rule", target=0.20
    ))
    updated = await service.update_rule(db_session, created.id, RuleUpdate(
        target=0.35
    ))
    assert updated is not None
    assert float(updated.target) == 0.35
    assert updated.description == "Target Rule"


@pytest.mark.asyncio
async def test_create_rule_with_tags(db_session):
    data = RuleCreate(
        description="Tag Rule",
        tags=["defensive", "conservative"],
    )
    rule = await service.create_rule(db_session, data)
    assert rule.tags == ["defensive", "conservative"]


@pytest.mark.asyncio
async def test_create_rule_with_absolute_target(db_session):
    rule = await service.create_rule(db_session, RuleCreate(
        description="Absolute target",
        target=5000,
        asset_class="equity",
    ))
    assert float(rule.target) == 5000
    assert rule.min is None
    assert rule.max is None
    assert rule.current is True


@pytest.mark.asyncio
async def test_create_rule_with_min_and_max(db_session):
    rule = await service.create_rule(db_session, RuleCreate(
        description="Range rule",
        min=0.10,
        max=0.30,
        asset_class="equity",
    ))
    assert float(rule.min) == 0.10
    assert float(rule.max) == 0.30
    assert rule.target is None


@pytest.mark.asyncio
async def test_update_rule_from_target_to_range(db_session):
    created = await service.create_rule(db_session, RuleCreate(
        description="Switchable Rule",
        target=0.20,
    ))
    updated = await service.update_rule(db_session, created.id, RuleUpdate(
        target=None,
        min=0.10,
        max=0.40,
    ))
    assert updated is not None
    assert updated.target is None
    assert float(updated.min) == 0.10
    assert float(updated.max) == 0.40


def test_rule_create_rejects_target_and_min():
    with pytest.raises(ValidationError):
        RuleCreate(description="Invalid", target=0.20, min=0.10)


def test_rule_create_rejects_target_and_max():
    with pytest.raises(ValidationError):
        RuleCreate(description="Invalid", target=0.20, max=0.30)


@pytest.mark.asyncio
async def test_create_invested_based_rule(db_session):
    rule = await service.create_rule(db_session, RuleCreate(
        description="Invested rule",
        target=0.15,
        current=False,
    ))
    assert float(rule.target) == 0.15
    assert rule.current is False
