import pytest

from bed.models.asset import Asset, AssetClass, AssetType
from bed.models.bond import Bond
from bed.services import bonds as service


class TestListBonds:
    async def test_empty(self, db_session):
        result = await service.list_bonds(db_session)
        assert result == []

    async def test_returns_ordered(self, db_session):
        db_session.add(Bond(name="tesouro selic 2029", price=15000.0))
        db_session.add(Bond(name="tesouro ipca+ 2035", price=3200.0))
        await db_session.commit()

        result = await service.list_bonds(db_session)
        assert len(result) == 2
        assert result[0].name == "tesouro ipca+ 2035"
        assert result[1].name == "tesouro selic 2029"


class TestGetBond:
    async def test_found(self, db_session):
        db_session.add(Bond(name="tesouro selic 2029", price=15000.0))
        await db_session.commit()

        result = await service.get_bond(db_session, "tesouro selic 2029")
        assert result is not None
        assert result.price == 15000.0

    async def test_not_found(self, db_session):
        result = await service.get_bond(db_session, "nope")
        assert result is None


class TestAddBond:
    async def test_add(self, db_session):
        result = await service.add_bond(db_session, "tesouro prefixado 2027")
        assert result.name == "tesouro prefixado 2027"
        assert result.price == 0

        fetched = await service.get_bond(db_session, "tesouro prefixado 2027")
        assert fetched is not None


class TestRemoveBond:
    async def test_remove_existing(self, db_session):
        db_session.add(Bond(name="tesouro selic 2029", price=15000.0))
        await db_session.commit()

        assert await service.remove_bond(db_session, "tesouro selic 2029") is True
        assert await service.get_bond(db_session, "tesouro selic 2029") is None

    async def test_remove_missing(self, db_session):
        assert await service.remove_bond(db_session, "nope") is False


class TestGetBondAssets:
    async def test_returns_only_bonds(self, db_session):
        db_session.add(Asset(
            name="tesouro selic 2029", asset_class=AssetClass.fixed_income, asset_type=AssetType.bond,
            quantity=1, initial_value=10000, current_value=15000,
        ))
        db_session.add(Asset(
            name="petr4", asset_class=AssetClass.equity, asset_type=AssetType.stock,
            quantity=100, initial_value=3000, current_value=3000,
        ))
        await db_session.commit()

        result = await service.get_bond_assets(db_session)
        assert len(result) == 1
        assert result[0].name == "tesouro selic 2029"


class TestFetchPrices:
    def test_returns_dict(self, monkeypatch):
        sample_response = {
            "response": {
                "TrsrBdTradgList": [
                    {
                        "TrsrBd": {
                            "nm": "Tesouro Selic 2029",
                            "untrRedVal": 15432.10,
                        }
                    },
                    {
                        "TrsrBd": {
                            "nm": "Tesouro IPCA+ 2035",
                            "untrRedVal": 3210.50,
                        }
                    },
                ]
            }
        }

        import json
        from unittest.mock import MagicMock

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(sample_response).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        def mock_urlopen(req, timeout=None):
            return mock_resp

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

        prices = service.fetch_prices()
        assert "tesouro selic 2029" in prices
        assert prices["tesouro selic 2029"] == 15432.10
        assert prices["tesouro ipca+ 2035"] == 3210.50

    def test_returns_empty_on_failure(self, monkeypatch):
        def mock_urlopen(req, timeout=None):
            raise Exception("network error")

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

        prices = service.fetch_prices()
        assert prices == {}

    def test_falls_back_to_next_url(self, monkeypatch):
        """When the first URL fails, the second URL should be tried."""
        sample_response = {
            "response": {
                "TrsrBdTradgList": [
                    {"TrsrBd": {"nm": "Tesouro Selic 2029", "untrRedVal": 15000.0}},
                ]
            }
        }

        import json
        from unittest.mock import MagicMock

        call_count = 0

        def mock_urlopen(req, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("first URL down")
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(sample_response).encode()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

        prices = service.fetch_prices()
        assert call_count == 2
        assert prices["tesouro selic 2029"] == 15000.0


class TestSearchBonds:
    def test_partial_match(self):
        available = {
            "tesouro selic 2027": 14000.0,
            "tesouro selic 2029": 15000.0,
            "tesouro ipca+ 2035": 3200.0,
        }
        results = service.search_bonds("selic", available)
        assert len(results) == 2
        assert results[0][0] == "tesouro selic 2027"
        assert results[1][0] == "tesouro selic 2029"

    def test_no_match(self):
        available = {"tesouro selic 2029": 15000.0}
        results = service.search_bonds("prefixado", available)
        assert results == []


class TestUpdatePrices:
    async def test_updates_bond_and_asset(self, db_session, monkeypatch):
        db_session.add(Bond(name="tesouro selic 2029", price=0))
        db_session.add(Asset(
            name="tesouro ipca+ 2035", asset_class=AssetClass.fixed_income, asset_type=AssetType.bond,
            quantity=2, initial_value=5000, current_value=5000,
        ))
        await db_session.commit()

        monkeypatch.setattr(
            service, "fetch_prices",
            lambda: {"tesouro selic 2029": 15000.0, "tesouro ipca+ 2035": 3200.0},
        )

        prices = await service.update_prices(db_session)
        assert prices["tesouro selic 2029"] == 15000.0
        assert prices["tesouro ipca+ 2035"] == 3200.0

        bond = await service.get_bond(db_session, "tesouro selic 2029")
        assert bond.price == 15000.0

        # ipca+ should also have a bond entry now
        ipca_bond = await service.get_bond(db_session, "tesouro ipca+ 2035")
        assert ipca_bond is not None
        assert ipca_bond.price == 3200.0

        # Asset current_value = quantity * price = 2 * 3200 = 6400
        assets = await service.get_bond_assets(db_session)
        assert float(assets[0].current_value) == 6400.0

    async def test_matches_hyphenated_names(self, db_session, monkeypatch):
        """Bond names stored with hyphens should match API names with spaces."""
        db_session.add(Bond(name="tesouro-selic-2029", price=0))
        db_session.add(Bond(name="tesouro-ipca-2035", price=0))
        await db_session.commit()

        monkeypatch.setattr(
            service, "fetch_prices",
            lambda: {"tesouro selic 2029": 15000.0, "tesouro ipca+ 2035": 3200.0},
        )

        prices = await service.update_prices(db_session)
        assert prices["tesouro-selic-2029"] == 15000.0
        assert prices["tesouro-ipca-2035"] == 3200.0

        bond = await service.get_bond(db_session, "tesouro-selic-2029")
        assert bond.price == 15000.0

    async def test_empty(self, db_session, monkeypatch):
        monkeypatch.setattr(service, "fetch_prices", lambda: {})
        prices = await service.update_prices(db_session)
        assert prices == {}
