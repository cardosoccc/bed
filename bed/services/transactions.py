import hashlib
import uuid
from datetime import date

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from bed.models.transaction import Transaction
from bed.schemas.transaction import TransactionCreate, TransactionUpdate


async def list_transactions(
    db: AsyncSession,
    ticker: str | None = None,
    type_filter: str | None = None,
    institution: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int | None = 50,
) -> list[Transaction]:
    query = select(Transaction).order_by(desc(Transaction.date), desc(Transaction.created_at))
    if ticker:
        query = query.where(Transaction.ticker == ticker)
    if type_filter:
        query = query.where(Transaction.type == type_filter)
    if institution:
        query = query.where(Transaction.institution == institution)
    if date_from:
        query = query.where(Transaction.date >= date_from)
    if date_to:
        query = query.where(Transaction.date <= date_to)
    if limit:
        query = query.limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_transaction(db: AsyncSession, txn_id: uuid.UUID) -> Transaction | None:
    return await db.get(Transaction, txn_id)


async def create_transaction(db: AsyncSession, data: TransactionCreate) -> Transaction:
    txn = Transaction(**data.model_dump())
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    return txn


async def update_transaction(db: AsyncSession, txn_id: uuid.UUID, data: TransactionUpdate) -> Transaction | None:
    txn = await db.get(Transaction, txn_id)
    if not txn:
        return None
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(txn, key, value)
    await db.commit()
    await db.refresh(txn)
    return txn


async def delete_transaction(db: AsyncSession, txn_id: uuid.UUID) -> bool:
    txn = await db.get(Transaction, txn_id)
    if not txn:
        return False
    await db.delete(txn)
    await db.commit()
    return True


async def bulk_create_transactions(db: AsyncSession, items: list[TransactionCreate]) -> tuple[int, int]:
    """Returns (imported_count, skipped_count)."""
    result = await db.execute(select(Transaction.row_hash).where(Transaction.row_hash.isnot(None)))
    existing_hashes = {row[0] for row in result.all()}

    imported = 0
    skipped = 0
    for data in items:
        if data.row_hash and data.row_hash in existing_hashes:
            skipped += 1
            continue
        txn = Transaction(**data.model_dump())
        db.add(txn)
        if data.row_hash:
            existing_hashes.add(data.row_hash)
        imported += 1

    await db.commit()
    return imported, skipped


def compute_row_hash(
    date_val: date,
    type_val: str,
    product: str,
    institution: str,
    quantity: float,
    unit_value: float,
    total_value: float,
) -> str:
    key = f"{date_val}|{type_val}|{product}|{institution}|{quantity}|{unit_value}|{total_value}"
    return hashlib.sha256(key.encode()).hexdigest()
