import uuid
from datetime import date

import pytest

from bed.schemas.transaction import TransactionCreate, TransactionUpdate
from bed.services import transactions as service
from bed.services.transactions import compute_row_hash


@pytest.mark.asyncio
async def test_create_transaction(db_session):
    data = TransactionCreate(
        date=date(2026, 3, 26),
        type="Transferência - Liquidação",
        product="CSAN3 - COSAN SA",
        ticker="CSAN3",
        institution="inter",
        quantity=2600,
        unit_value=5.43,
        total_value=14118.00,
        tags=["dividendos"],
    )
    txn = await service.create_transaction(db_session, data)
    assert txn.id is not None
    assert txn.date == date(2026, 3, 26)
    assert txn.type == "Transferência - Liquidação"
    assert txn.product == "CSAN3 - COSAN SA"
    assert txn.ticker == "CSAN3"
    assert txn.institution == "inter"
    assert float(txn.quantity) == 2600
    assert float(txn.unit_value) == 5.43
    assert float(txn.total_value) == 14118.00
    assert txn.tags == ["dividendos"]


@pytest.mark.asyncio
async def test_list_transactions(db_session):
    for i in range(3):
        await service.create_transaction(db_session, TransactionCreate(
            date=date(2026, 3, 20 + i),
            type="Compra",
            product=f"ASSET{i}",
            institution="inter",
        ))
    txns = await service.list_transactions(db_session)
    assert len(txns) == 3
    # Should be ordered by date desc
    assert txns[0].date >= txns[1].date >= txns[2].date


@pytest.mark.asyncio
async def test_list_transactions_with_filters(db_session):
    await service.create_transaction(db_session, TransactionCreate(
        date=date(2026, 1, 10), type="Compra", product="PETR4 - PETROBRAS",
        ticker="PETR4", institution="inter",
    ))
    await service.create_transaction(db_session, TransactionCreate(
        date=date(2026, 2, 15), type="Dividendo", product="PETR4 - PETROBRAS",
        ticker="PETR4", institution="btg-pactual",
    ))
    await service.create_transaction(db_session, TransactionCreate(
        date=date(2026, 3, 20), type="Compra", product="VALE3 - VALE",
        ticker="VALE3", institution="inter",
    ))

    # Filter by ticker
    result = await service.list_transactions(db_session, ticker="PETR4")
    assert len(result) == 2

    # Filter by type
    result = await service.list_transactions(db_session, type_filter="Dividendo")
    assert len(result) == 1
    assert result[0].type == "Dividendo"

    # Filter by institution
    result = await service.list_transactions(db_session, institution="btg-pactual")
    assert len(result) == 1

    # Filter by date range
    result = await service.list_transactions(
        db_session, date_from=date(2026, 2, 1), date_to=date(2026, 2, 28),
    )
    assert len(result) == 1
    assert result[0].date == date(2026, 2, 15)

    # Filter with limit
    result = await service.list_transactions(db_session, limit=2)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_transaction(db_session):
    created = await service.create_transaction(db_session, TransactionCreate(
        date=date(2026, 3, 26), type="Compra", product="PETR4", institution="inter",
    ))
    fetched = await service.get_transaction(db_session, created.id)
    assert fetched is not None
    assert fetched.product == "PETR4"


@pytest.mark.asyncio
async def test_get_transaction_not_found(db_session):
    result = await service.get_transaction(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_update_transaction(db_session):
    created = await service.create_transaction(db_session, TransactionCreate(
        date=date(2026, 3, 26), type="Compra", product="PETR4",
        institution="inter", quantity=100, total_value=4600,
    ))
    updated = await service.update_transaction(
        db_session, created.id,
        TransactionUpdate(total_value=4700, tags=["energia"]),
    )
    assert updated is not None
    assert updated.total_value == 4700
    assert updated.tags == ["energia"]
    assert updated.quantity == 100  # unchanged


@pytest.mark.asyncio
async def test_update_transaction_not_found(db_session):
    result = await service.update_transaction(
        db_session, uuid.uuid4(), TransactionUpdate(type="Venda"),
    )
    assert result is None


@pytest.mark.asyncio
async def test_delete_transaction(db_session):
    created = await service.create_transaction(db_session, TransactionCreate(
        date=date(2026, 3, 26), type="Compra", product="DEL", institution="inter",
    ))
    assert await service.delete_transaction(db_session, created.id) is True
    assert await service.get_transaction(db_session, created.id) is None


@pytest.mark.asyncio
async def test_delete_transaction_not_found(db_session):
    assert await service.delete_transaction(db_session, uuid.uuid4()) is False


@pytest.mark.asyncio
async def test_bulk_create_transactions(db_session):
    items = [
        TransactionCreate(
            date=date(2026, 3, i + 1), type="Compra", product=f"ASSET{i}",
            institution="inter", row_hash=f"hash{i}",
        )
        for i in range(5)
    ]
    imported, skipped = await service.bulk_create_transactions(db_session, items)
    assert imported == 5
    assert skipped == 0

    txns = await service.list_transactions(db_session, limit=None)
    assert len(txns) == 5


@pytest.mark.asyncio
async def test_bulk_create_skips_duplicates(db_session):
    items = [
        TransactionCreate(
            date=date(2026, 3, 1), type="Compra", product="PETR4",
            institution="inter", row_hash="duplicate_hash",
        ),
    ]
    imported, skipped = await service.bulk_create_transactions(db_session, items)
    assert imported == 1
    assert skipped == 0

    # Import same hash again
    imported, skipped = await service.bulk_create_transactions(db_session, items)
    assert imported == 0
    assert skipped == 1

    txns = await service.list_transactions(db_session, limit=None)
    assert len(txns) == 1


@pytest.mark.asyncio
async def test_bulk_create_skips_duplicates_within_batch(db_session):
    items = [
        TransactionCreate(
            date=date(2026, 3, 1), type="Compra", product="PETR4",
            institution="inter", row_hash="same_hash",
        ),
        TransactionCreate(
            date=date(2026, 3, 1), type="Compra", product="PETR4",
            institution="inter", row_hash="same_hash",
        ),
    ]
    imported, skipped = await service.bulk_create_transactions(db_session, items)
    assert imported == 1
    assert skipped == 1


def test_compute_row_hash():
    h1 = compute_row_hash(date(2026, 3, 26), "Compra", "PETR4", "inter", 100, 46.0, 4600.0)
    h2 = compute_row_hash(date(2026, 3, 26), "Compra", "PETR4", "inter", 100, 46.0, 4600.0)
    h3 = compute_row_hash(date(2026, 3, 27), "Compra", "PETR4", "inter", 100, 46.0, 4600.0)
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64  # SHA-256 hex digest
