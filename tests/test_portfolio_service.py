import pytest

from bed.models.asset import AssetClass, AssetType
from bed.schemas.asset import AssetCreate
from bed.schemas.rule import RuleCreate
from bed.services import assets as asset_service
from bed.services import rules as rule_service
from bed.services.portfolio import get_portfolio_status


@pytest.mark.asyncio
async def test_empty_portfolio(db_session):
    status = await get_portfolio_status(db_session)
    assert status.assets == []
    assert status.total_initial == 0.0
    assert status.total_current == 0.0
    assert status.classes == []
    assert status.tags == []


@pytest.mark.asyncio
async def test_totals(db_session):
    await asset_service.create_asset(db_session, AssetCreate(
        name="A", asset_class=AssetClass.equity, asset_type=AssetType.stock,
        initial_value=10000, current_value=12000,
    ))
    await asset_service.create_asset(db_session, AssetCreate(
        name="B", asset_class=AssetClass.fixed_income, asset_type=AssetType.bond,
        initial_value=5000, current_value=5200,
    ))
    status = await get_portfolio_status(db_session)
    assert len(status.assets) == 2
    assert status.total_initial == 15000
    assert status.total_current == 17200


@pytest.mark.asyncio
async def test_class_breakdown(db_session):
    await asset_service.create_asset(db_session, AssetCreate(
        name="S1", asset_class=AssetClass.equity, asset_type=AssetType.stock,
        current_value=8000,
    ))
    await asset_service.create_asset(db_session, AssetCreate(
        name="B1", asset_class=AssetClass.fixed_income, asset_type=AssetType.bond,
        current_value=2000,
    ))
    status = await get_portfolio_status(db_session)
    assert len(status.classes) == 2

    equity = next(c for c in status.classes if c.name == "equity")
    fixed = next(c for c in status.classes if c.name == "fixed-income")

    assert equity.total == 8000
    assert equity.pct == pytest.approx(80.0)
    assert fixed.total == 2000
    assert fixed.pct == pytest.approx(20.0)


@pytest.mark.asyncio
async def test_class_with_rules(db_session):
    await asset_service.create_asset(db_session, AssetCreate(
        name="S1", asset_class=AssetClass.equity, asset_type=AssetType.stock,
        current_value=8000,
    ))
    await asset_service.create_asset(db_session, AssetCreate(
        name="B1", asset_class=AssetClass.fixed_income, asset_type=AssetType.bond,
        current_value=2000,
    ))
    await rule_service.create_rule(db_session, RuleCreate(
        description="60% equity", proportion=0.60, asset_class="equity",
    ))
    await rule_service.create_rule(db_session, RuleCreate(
        description="40% bonds", proportion=0.40, asset_class="fixed-income",
    ))

    status = await get_portfolio_status(db_session)
    equity = next(c for c in status.classes if c.name == "equity")
    fixed = next(c for c in status.classes if c.name == "fixed-income")

    assert equity.target == pytest.approx(6000)
    assert equity.target_pct == pytest.approx(60)
    assert equity.diff == pytest.approx(2000)

    assert fixed.target == pytest.approx(4000)
    assert fixed.target_pct == pytest.approx(40)
    assert fixed.diff == pytest.approx(-2000)


@pytest.mark.asyncio
async def test_tag_breakdown(db_session):
    await asset_service.create_asset(db_session, AssetCreate(
        name="S1", asset_class=AssetClass.equity, asset_type=AssetType.stock,
        current_value=6000, tags=["growth", "us"],
    ))
    await asset_service.create_asset(db_session, AssetCreate(
        name="B1", asset_class=AssetClass.fixed_income, asset_type=AssetType.bond,
        current_value=4000, tags=["defensive"],
    ))

    status = await get_portfolio_status(db_session)
    assert len(status.tags) == 3

    growth = next(t for t in status.tags if t.name == "growth")
    assert growth.total == 6000
    assert growth.pct == pytest.approx(60.0)

    us = next(t for t in status.tags if t.name == "us")
    assert us.total == 6000
    assert us.pct == pytest.approx(60.0)

    defensive = next(t for t in status.tags if t.name == "defensive")
    assert defensive.total == 4000
    assert defensive.pct == pytest.approx(40.0)


@pytest.mark.asyncio
async def test_tag_with_rules(db_session):
    await asset_service.create_asset(db_session, AssetCreate(
        name="S1", asset_class=AssetClass.equity, asset_type=AssetType.stock,
        current_value=6000, tags=["growth"],
    ))
    await asset_service.create_asset(db_session, AssetCreate(
        name="B1", asset_class=AssetClass.fixed_income, asset_type=AssetType.bond,
        current_value=4000, tags=["defensive"],
    ))
    await rule_service.create_rule(db_session, RuleCreate(
        description="50% growth", proportion=0.50, tags=["growth"],
    ))

    status = await get_portfolio_status(db_session)
    growth = next(t for t in status.tags if t.name == "growth")
    assert growth.target == pytest.approx(5000)
    assert growth.target_pct == pytest.approx(50)
    assert growth.diff == pytest.approx(1000)

    defensive = next(t for t in status.tags if t.name == "defensive")
    assert defensive.target == 4000
    assert defensive.target_pct == pytest.approx(40.0)
    assert defensive.diff == 0.0


@pytest.mark.asyncio
async def test_class_with_min_proportion_below(db_session):
    """When actual is below min, diff = total - min_value (negative)."""
    await asset_service.create_asset(db_session, AssetCreate(
        name="S1", asset_class=AssetClass.equity, asset_type=AssetType.stock,
        current_value=4000,
    ))
    await asset_service.create_asset(db_session, AssetCreate(
        name="B1", asset_class=AssetClass.fixed_income, asset_type=AssetType.bond,
        current_value=6000,
    ))
    # equity target=60%, min=50%, max=70%
    await rule_service.create_rule(db_session, RuleCreate(
        description="equity band", proportion=0.60,
        min_proportion=0.50, max_proportion=0.70,
        asset_class="equity",
    ))

    status = await get_portfolio_status(db_session)
    equity = next(c for c in status.classes if c.name == "equity")
    # total=4000, target=6000, min=5000, max=7000
    assert equity.target == pytest.approx(6000)
    assert equity.target_pct == pytest.approx(60)
    # 4000 < 5000 (min), so diff = 4000 - 5000 = -1000
    assert equity.diff == pytest.approx(-1000)


@pytest.mark.asyncio
async def test_class_with_max_proportion_above(db_session):
    """When actual is above max, diff = total - max_value (positive)."""
    await asset_service.create_asset(db_session, AssetCreate(
        name="S1", asset_class=AssetClass.equity, asset_type=AssetType.stock,
        current_value=8000,
    ))
    await asset_service.create_asset(db_session, AssetCreate(
        name="B1", asset_class=AssetClass.fixed_income, asset_type=AssetType.bond,
        current_value=2000,
    ))
    await rule_service.create_rule(db_session, RuleCreate(
        description="equity band", proportion=0.60,
        min_proportion=0.50, max_proportion=0.70,
        asset_class="equity",
    ))

    status = await get_portfolio_status(db_session)
    equity = next(c for c in status.classes if c.name == "equity")
    # total=8000, max=7000
    # 8000 > 7000, so diff = 8000 - 7000 = 1000
    assert equity.diff == pytest.approx(1000)


@pytest.mark.asyncio
async def test_class_within_band_diff_zero(db_session):
    """When actual is within [min, max] band, diff = 0."""
    await asset_service.create_asset(db_session, AssetCreate(
        name="S1", asset_class=AssetClass.equity, asset_type=AssetType.stock,
        current_value=6000,
    ))
    await asset_service.create_asset(db_session, AssetCreate(
        name="B1", asset_class=AssetClass.fixed_income, asset_type=AssetType.bond,
        current_value=4000,
    ))
    await rule_service.create_rule(db_session, RuleCreate(
        description="equity band", proportion=0.60,
        min_proportion=0.50, max_proportion=0.70,
        asset_class="equity",
    ))

    status = await get_portfolio_status(db_session)
    equity = next(c for c in status.classes if c.name == "equity")
    # total=6000, min=5000, max=7000 → within band
    assert equity.target == pytest.approx(6000)
    assert equity.diff == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_class_with_min_only(db_session):
    """Rule with only min_proportion: diff=0 when above min, negative when below."""
    await asset_service.create_asset(db_session, AssetCreate(
        name="S1", asset_class=AssetClass.equity, asset_type=AssetType.stock,
        current_value=3000,
    ))
    await asset_service.create_asset(db_session, AssetCreate(
        name="B1", asset_class=AssetClass.fixed_income, asset_type=AssetType.bond,
        current_value=7000,
    ))
    await rule_service.create_rule(db_session, RuleCreate(
        description="equity min", proportion=0.50,
        min_proportion=0.40,
        asset_class="equity",
    ))

    status = await get_portfolio_status(db_session)
    equity = next(c for c in status.classes if c.name == "equity")
    # total=3000, min=4000 → below min
    assert equity.diff == pytest.approx(-1000)


@pytest.mark.asyncio
async def test_class_with_min_only_above(db_session):
    """Rule with only min_proportion: diff=0 when actual is above min."""
    await asset_service.create_asset(db_session, AssetCreate(
        name="S1", asset_class=AssetClass.equity, asset_type=AssetType.stock,
        current_value=6000,
    ))
    await asset_service.create_asset(db_session, AssetCreate(
        name="B1", asset_class=AssetClass.fixed_income, asset_type=AssetType.bond,
        current_value=4000,
    ))
    await rule_service.create_rule(db_session, RuleCreate(
        description="equity min", proportion=0.50,
        min_proportion=0.40,
        asset_class="equity",
    ))

    status = await get_portfolio_status(db_session)
    equity = next(c for c in status.classes if c.name == "equity")
    # total=6000, min=4000 → above min, diff=0
    assert equity.diff == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_class_with_max_only(db_session):
    """Rule with only max_proportion: diff=0 when below max, positive when above."""
    await asset_service.create_asset(db_session, AssetCreate(
        name="S1", asset_class=AssetClass.equity, asset_type=AssetType.stock,
        current_value=8000,
    ))
    await asset_service.create_asset(db_session, AssetCreate(
        name="B1", asset_class=AssetClass.fixed_income, asset_type=AssetType.bond,
        current_value=2000,
    ))
    await rule_service.create_rule(db_session, RuleCreate(
        description="equity max", proportion=0.60,
        max_proportion=0.70,
        asset_class="equity",
    ))

    status = await get_portfolio_status(db_session)
    equity = next(c for c in status.classes if c.name == "equity")
    # total=8000, max=7000 → above max
    assert equity.diff == pytest.approx(1000)


@pytest.mark.asyncio
async def test_class_with_max_only_below(db_session):
    """Rule with only max_proportion: diff=0 when below max."""
    await asset_service.create_asset(db_session, AssetCreate(
        name="S1", asset_class=AssetClass.equity, asset_type=AssetType.stock,
        current_value=6000,
    ))
    await asset_service.create_asset(db_session, AssetCreate(
        name="B1", asset_class=AssetClass.fixed_income, asset_type=AssetType.bond,
        current_value=4000,
    ))
    await rule_service.create_rule(db_session, RuleCreate(
        description="equity max", proportion=0.60,
        max_proportion=0.70,
        asset_class="equity",
    ))

    status = await get_portfolio_status(db_session)
    equity = next(c for c in status.classes if c.name == "equity")
    # total=6000, max=7000 → below max, diff=0
    assert equity.diff == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_tag_with_min_max(db_session):
    """Tag rules also support min/max proportion bands."""
    await asset_service.create_asset(db_session, AssetCreate(
        name="S1", asset_class=AssetClass.equity, asset_type=AssetType.stock,
        current_value=6000, tags=["growth"],
    ))
    await asset_service.create_asset(db_session, AssetCreate(
        name="B1", asset_class=AssetClass.fixed_income, asset_type=AssetType.bond,
        current_value=4000, tags=["defensive"],
    ))
    await rule_service.create_rule(db_session, RuleCreate(
        description="growth band", proportion=0.50,
        min_proportion=0.40, max_proportion=0.70,
        tags=["growth"],
    ))

    status = await get_portfolio_status(db_session)
    growth = next(t for t in status.tags if t.name == "growth")
    # total=6000, min=4000, max=7000 → within band
    assert growth.diff == pytest.approx(0.0)
    assert growth.target == pytest.approx(5000)


@pytest.mark.asyncio
async def test_no_min_max_falls_back_to_target(db_session):
    """Without min/max, diff is calculated against proportion target (existing behavior)."""
    await asset_service.create_asset(db_session, AssetCreate(
        name="S1", asset_class=AssetClass.equity, asset_type=AssetType.stock,
        current_value=8000,
    ))
    await asset_service.create_asset(db_session, AssetCreate(
        name="B1", asset_class=AssetClass.fixed_income, asset_type=AssetType.bond,
        current_value=2000,
    ))
    await rule_service.create_rule(db_session, RuleCreate(
        description="60% equity", proportion=0.60,
        asset_class="equity",
    ))

    status = await get_portfolio_status(db_session)
    equity = next(c for c in status.classes if c.name == "equity")
    # No min/max → diff = total - target = 8000 - 6000 = 2000
    assert equity.diff == pytest.approx(2000)


@pytest.mark.asyncio
async def test_class_from_rule_only(db_session):
    """A class appears in breakdown even if no assets have that class, but a rule does."""
    await asset_service.create_asset(db_session, AssetCreate(
        name="S1", asset_class=AssetClass.equity, asset_type=AssetType.stock,
        current_value=10000,
    ))
    await rule_service.create_rule(db_session, RuleCreate(
        description="30% bonds", proportion=0.30, asset_class="fixed-income",
    ))

    status = await get_portfolio_status(db_session)
    fixed = next(c for c in status.classes if c.name == "fixed-income")
    assert fixed.total == 0.0
    assert fixed.target == pytest.approx(3000)
    assert fixed.diff == pytest.approx(-3000)
