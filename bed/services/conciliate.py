from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bed.models.asset import Asset, AssetType
from bed.models.transaction import Transaction


EQUITY_TYPES = {AssetType.stock, AssetType.etf, AssetType.reit, AssetType.fund}
TRADE_TYPES = {"Compra", "Venda"}


@dataclass
class Position:
    ticker: str
    quantity: float = 0
    total_invested: float = 0
    total_sold: float = 0
    buy_qty: float = 0


@dataclass
class Mismatch:
    ticker: str
    txn_qty: float
    asset_qty: float


@dataclass
class MissingAsset:
    ticker: str
    txn_qty: float


@dataclass
class ConciliationReport:
    matches: list[str] = field(default_factory=list)
    mismatches: list[Mismatch] = field(default_factory=list)
    missing_assets: list[MissingAsset] = field(default_factory=list)
    orphan_assets: list[Asset] = field(default_factory=list)


async def consolidate_positions(db: AsyncSession) -> dict[str, Position]:
    """Consolidate buy/sell transactions by ticker into net positions."""
    query = (
        select(Transaction)
        .where(Transaction.type.in_(TRADE_TYPES))
        .where(Transaction.ticker.isnot(None))
    )
    result = await db.execute(query)
    transactions = result.scalars().all()

    positions: dict[str, Position] = defaultdict(lambda: Position(ticker=""))

    for txn in transactions:
        pos = positions[txn.ticker]
        pos.ticker = txn.ticker
        qty = float(txn.quantity)

        if txn.type == "Compra":
            pos.quantity += qty
            pos.buy_qty += qty
            pos.total_invested += float(txn.total_value)
        elif txn.type == "Venda":
            pos.quantity -= qty
            pos.total_sold += abs(float(txn.total_value))

    # Filter to active positions (qty > 0)
    return {t: p for t, p in positions.items() if p.quantity > 0}


async def conciliate(db: AsyncSession) -> ConciliationReport:
    """Compare consolidated transaction positions against assets."""
    positions = await consolidate_positions(db)

    query = select(Asset).where(Asset.asset_type.in_(EQUITY_TYPES))
    result = await db.execute(query)
    assets = {a.name.upper(): a for a in result.scalars().all()}

    report = ConciliationReport()
    matched_asset_keys = set()

    for ticker, pos in sorted(positions.items()):
        ticker_upper = ticker.upper()
        if ticker_upper in assets:
            matched_asset_keys.add(ticker_upper)
            asset = assets[ticker_upper]
            asset_qty = float(asset.quantity)
            if abs(pos.quantity - asset_qty) < 0.0001:
                report.matches.append(ticker)
            else:
                report.mismatches.append(Mismatch(
                    ticker=ticker,
                    txn_qty=pos.quantity,
                    asset_qty=asset_qty,
                ))
        else:
            report.missing_assets.append(MissingAsset(
                ticker=ticker,
                txn_qty=pos.quantity,
            ))

    for name, asset in sorted(assets.items()):
        if name not in matched_asset_keys:
            report.orphan_assets.append(asset)

    return report
