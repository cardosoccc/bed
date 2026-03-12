import pytest

from bed.models.asset import Asset, AssetClass, AssetType
from bed.models.ticker import Ticker
from bed.services import stocks as service


class TestListTickers:
    async def test_empty(self, db_session):
        result = await service.list_tickers(db_session)
        assert result == []

    async def test_returns_ordered(self, db_session):
        db_session.add(Ticker(ticker="petr4", price=30.0))
        db_session.add(Ticker(ticker="bbas3", price=25.0))
        await db_session.commit()

        result = await service.list_tickers(db_session)
        assert len(result) == 2
        assert result[0].ticker == "bbas3"
        assert result[1].ticker == "petr4"


class TestGetTicker:
    async def test_found(self, db_session):
        db_session.add(Ticker(ticker="vale3", price=60.0))
        await db_session.commit()

        result = await service.get_ticker(db_session, "vale3")
        assert result is not None
        assert result.price == 60.0

    async def test_not_found(self, db_session):
        result = await service.get_ticker(db_session, "nope")
        assert result is None


class TestAddTicker:
    async def test_add(self, db_session):
        result = await service.add_ticker(db_session, "itub4")
        assert result.ticker == "itub4"
        assert result.price == 0

        fetched = await service.get_ticker(db_session, "itub4")
        assert fetched is not None


class TestRemoveTicker:
    async def test_remove_existing(self, db_session):
        db_session.add(Ticker(ticker="mglu3", price=5.0))
        await db_session.commit()

        assert await service.remove_ticker(db_session, "mglu3") is True
        assert await service.get_ticker(db_session, "mglu3") is None

    async def test_remove_missing(self, db_session):
        assert await service.remove_ticker(db_session, "nope") is False


class TestGetStockAssets:
    async def test_returns_only_stocks(self, db_session):
        db_session.add(Asset(
            name="petr4", asset_class=AssetClass.equity, asset_type=AssetType.stock,
            quantity=100, initial_value=3000, current_value=3000,
        ))
        db_session.add(Asset(
            name="cdb", asset_class=AssetClass.fixed_income, asset_type=AssetType.bond,
            quantity=1, initial_value=1000, current_value=1050,
        ))
        await db_session.commit()

        result = await service.get_stock_assets(db_session)
        assert len(result) == 1
        assert result[0].name == "petr4"


class TestUpdatePrices:
    async def test_updates_ticker_and_asset(self, db_session, monkeypatch):
        db_session.add(Ticker(ticker="vale3", price=0))
        db_session.add(Asset(
            name="petr4", asset_class=AssetClass.equity, asset_type=AssetType.stock,
            quantity=100, initial_value=3000, current_value=3000,
        ))
        await db_session.commit()

        monkeypatch.setattr(
            service, "fetch_prices",
            lambda tickers: {t: 50.0 for t in tickers},
        )

        prices = await service.update_prices(db_session)
        assert prices["vale3"] == 50.0
        assert prices["petr4"] == 50.0

        ticker = await service.get_ticker(db_session, "vale3")
        assert ticker.price == 50.0

        # petr4 should also have a ticker entry now
        petr_ticker = await service.get_ticker(db_session, "petr4")
        assert petr_ticker is not None
        assert petr_ticker.price == 50.0

        # Asset current_value = quantity * price = 100 * 50 = 5000
        assets = await service.get_stock_assets(db_session)
        assert float(assets[0].current_value) == 5000.0

    async def test_empty(self, db_session, monkeypatch):
        monkeypatch.setattr(service, "fetch_prices", lambda tickers: {})
        prices = await service.update_prices(db_session)
        assert prices == {}
