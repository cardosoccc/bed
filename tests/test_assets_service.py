import pytest

from bed.models.asset import AssetClass, AssetType
from bed.schemas.asset import AssetCreate, AssetUpdate
from bed.services import assets as service


@pytest.mark.asyncio
async def test_create_asset(db_session):
    data = AssetCreate(
        name="AAPL",
        description="Apple Inc.",
        asset_class=AssetClass.equity,
        asset_type=AssetType.stock,
        quantity=100,
        initial_value=15000,
        current_value=17500,
        category="Tech",
    )
    asset = await service.create_asset(db_session, data)
    assert asset.name == "AAPL"
    assert asset.asset_class == AssetClass.equity
    assert asset.asset_type == AssetType.stock
    assert asset.quantity == 100
    assert asset.initial_value == 15000
    assert asset.current_value == 17500
    assert asset.category == "Tech"
    assert asset.id is not None


@pytest.mark.asyncio
async def test_list_assets(db_session):
    for name in ["AAPL", "GOOG", "MSFT"]:
        await service.create_asset(db_session, AssetCreate(
            name=name, asset_class=AssetClass.equity, asset_type=AssetType.stock
        ))
    assets = await service.list_assets(db_session)
    assert len(assets) == 3
    assert [a.name for a in assets] == ["AAPL", "GOOG", "MSFT"]


@pytest.mark.asyncio
async def test_get_asset(db_session):
    created = await service.create_asset(db_session, AssetCreate(
        name="TSLA", asset_class=AssetClass.equity, asset_type=AssetType.stock
    ))
    fetched = await service.get_asset(db_session, created.id)
    assert fetched is not None
    assert fetched.name == "TSLA"


@pytest.mark.asyncio
async def test_get_asset_not_found(db_session):
    import uuid
    result = await service.get_asset(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_update_asset(db_session):
    created = await service.create_asset(db_session, AssetCreate(
        name="BTC", asset_class=AssetClass.equity, asset_type=AssetType.crypto,
        quantity=1, initial_value=30000, current_value=45000,
    ))
    updated = await service.update_asset(db_session, created.id, AssetUpdate(
        current_value=50000, tags=["crypto", "volatile"]
    ))
    assert updated is not None
    assert updated.current_value == 50000
    assert updated.tags == ["crypto", "volatile"]
    assert updated.name == "BTC"  # unchanged


@pytest.mark.asyncio
async def test_update_asset_not_found(db_session):
    import uuid
    result = await service.update_asset(db_session, uuid.uuid4(), AssetUpdate(name="X"))
    assert result is None


@pytest.mark.asyncio
async def test_delete_asset(db_session):
    created = await service.create_asset(db_session, AssetCreate(
        name="DEL", asset_class=AssetClass.fixed_income, asset_type=AssetType.bond
    ))
    assert await service.delete_asset(db_session, created.id) is True
    assert await service.get_asset(db_session, created.id) is None


@pytest.mark.asyncio
async def test_delete_asset_not_found(db_session):
    import uuid
    assert await service.delete_asset(db_session, uuid.uuid4()) is False


@pytest.mark.asyncio
async def test_create_asset_with_tags(db_session):
    data = AssetCreate(
        name="ETF-XYZ",
        asset_class=AssetClass.equity,
        asset_type=AssetType.etf,
        tags=["index", "low-cost", "diversified"],
    )
    asset = await service.create_asset(db_session, data)
    assert asset.tags == ["index", "low-cost", "diversified"]
