from datetime import date

import pytest

from bed.models.asset import AssetClass, AssetType
from bed.schemas.asset import AssetCreate
from bed.schemas.transaction import TransactionCreate
from bed.services import assets as asset_service
from bed.services import transactions as txn_service
from bed.services.conciliate import conciliate, consolidate_positions


async def _create_txn(db, ticker, tipo, qty, unit, total):
    return await txn_service.create_transaction(db, TransactionCreate(
        date=date(2026, 1, 15),
        type=tipo,
        product=f"{ticker} - TEST",
        ticker=ticker,
        institution="inter",
        quantity=qty,
        unit_value=unit,
        total_value=total,
    ))


async def _create_asset(db, name, qty, asset_type=AssetType.stock):
    return await asset_service.create_asset(db, AssetCreate(
        name=name,
        asset_class=AssetClass.equity,
        asset_type=asset_type,
        quantity=qty,
    ))


@pytest.mark.asyncio
async def test_consolidate_single_buy(db_session):
    await _create_txn(db_session, "PETR4", "Compra", 100, 36.0, 3600.0)
    positions = await consolidate_positions(db_session)
    assert "PETR4" in positions
    assert positions["PETR4"].quantity == 100
    assert positions["PETR4"].total_invested == 3600.0


@pytest.mark.asyncio
async def test_consolidate_buy_and_sell(db_session):
    await _create_txn(db_session, "PETR4", "Compra", 200, 36.0, 7200.0)
    await _create_txn(db_session, "PETR4", "Venda", 100, 40.0, -4000.0)
    positions = await consolidate_positions(db_session)
    assert "PETR4" in positions
    assert positions["PETR4"].quantity == 100


@pytest.mark.asyncio
async def test_consolidate_fully_sold_excluded(db_session):
    await _create_txn(db_session, "VALE3", "Compra", 100, 70.0, 7000.0)
    await _create_txn(db_session, "VALE3", "Venda", 100, 75.0, -7500.0)
    positions = await consolidate_positions(db_session)
    assert "VALE3" not in positions


@pytest.mark.asyncio
async def test_consolidate_ignores_dividendos(db_session):
    await _create_txn(db_session, "PETR4", "Compra", 100, 36.0, 3600.0)
    await _create_txn(db_session, "PETR4", "Dividendo", 100, 0.5, 50.0)
    positions = await consolidate_positions(db_session)
    assert positions["PETR4"].quantity == 100


@pytest.mark.asyncio
async def test_consolidate_ignores_null_ticker(db_session):
    await txn_service.create_transaction(db_session, TransactionCreate(
        date=date(2026, 1, 15),
        type="Compra",
        product="Tesouro Selic 2031",
        ticker=None,
        institution="inter",
        quantity=1,
        unit_value=15000.0,
        total_value=15000.0,
    ))
    positions = await consolidate_positions(db_session)
    assert len(positions) == 0


@pytest.mark.asyncio
async def test_consolidate_multiple_tickers(db_session):
    await _create_txn(db_session, "PETR4", "Compra", 100, 36.0, 3600.0)
    await _create_txn(db_session, "VALE3", "Compra", 200, 70.0, 14000.0)
    await _create_txn(db_session, "BBAS3", "Compra", 300, 25.0, 7500.0)
    positions = await consolidate_positions(db_session)
    assert len(positions) == 3
    assert positions["PETR4"].quantity == 100
    assert positions["VALE3"].quantity == 200
    assert positions["BBAS3"].quantity == 300


@pytest.mark.asyncio
async def test_conciliate_all_match(db_session):
    await _create_txn(db_session, "PETR4", "Compra", 100, 36.0, 3600.0)
    await _create_asset(db_session, "PETR4", 100)
    report = await conciliate(db_session)
    assert len(report.matches) == 1
    assert len(report.mismatches) == 0
    assert len(report.missing_assets) == 0
    assert len(report.orphan_assets) == 0


@pytest.mark.asyncio
async def test_conciliate_qty_mismatch(db_session):
    await _create_txn(db_session, "PETR4", "Compra", 300, 36.0, 10800.0)
    await _create_asset(db_session, "PETR4", 200)
    report = await conciliate(db_session)
    assert len(report.mismatches) == 1
    assert report.mismatches[0].ticker == "PETR4"
    assert report.mismatches[0].txn_qty == 300
    assert report.mismatches[0].asset_qty == 200


@pytest.mark.asyncio
async def test_conciliate_missing_asset(db_session):
    await _create_txn(db_session, "CSAN3", "Compra", 2600, 5.0, 13000.0)
    report = await conciliate(db_session)
    assert len(report.missing_assets) == 1
    assert report.missing_assets[0].ticker == "CSAN3"


@pytest.mark.asyncio
async def test_conciliate_orphan_asset(db_session):
    await _create_asset(db_session, "BBDC4", 100)
    report = await conciliate(db_session)
    assert len(report.orphan_assets) == 1
    assert report.orphan_assets[0].name == "BBDC4"


@pytest.mark.asyncio
async def test_conciliate_bond_assets_excluded(db_session):
    await _create_asset(db_session, "Tesouro Selic 2031", 1, asset_type=AssetType.bond)
    report = await conciliate(db_session)
    assert len(report.orphan_assets) == 0


@pytest.mark.asyncio
async def test_conciliate_empty(db_session):
    report = await conciliate(db_session)
    assert len(report.matches) == 0
    assert len(report.mismatches) == 0
    assert len(report.missing_assets) == 0
    assert len(report.orphan_assets) == 0
