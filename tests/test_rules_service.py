import uuid

import pytest

from bed.schemas.rule import RuleCreate, RuleUpdate
from bed.services import rules as service


@pytest.mark.asyncio
async def test_create_rule(db_session):
    data = RuleCreate(
        description="Max 30% equity",
        current_value=30,
        asset_class="equity",
    )
    rule = await service.create_rule(db_session, data)
    assert rule.description == "Max 30% equity"
    assert rule.current_value == 30
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
        description="Test Rule", invested_value=50000
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
        description="Editable Rule", current_value=20
    ))
    updated = await service.update_rule(db_session, created.id, RuleUpdate(
        current_value=25, tags=["important"]
    ))
    assert updated is not None
    assert updated.current_value == 25
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
async def test_create_rule_with_proportion(db_session):
    data = RuleCreate(
        description="30% equity",
        proportion=0.30,
        asset_class="equity",
    )
    rule = await service.create_rule(db_session, data)
    assert rule.description == "30% equity"
    assert float(rule.proportion) == 0.30
    assert rule.asset_class == "equity"


@pytest.mark.asyncio
async def test_update_rule_proportion(db_session):
    created = await service.create_rule(db_session, RuleCreate(
        description="Proportion Rule", proportion=0.20
    ))
    updated = await service.update_rule(db_session, created.id, RuleUpdate(
        proportion=0.35
    ))
    assert updated is not None
    assert float(updated.proportion) == 0.35
    assert updated.description == "Proportion Rule"


@pytest.mark.asyncio
async def test_create_rule_with_tags(db_session):
    data = RuleCreate(
        description="Tag Rule",
        tags=["defensive", "conservative"],
    )
    rule = await service.create_rule(db_session, data)
    assert rule.tags == ["defensive", "conservative"]
