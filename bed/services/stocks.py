from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bed.models.asset import Asset, AssetType
from bed.models.stock import Stock


async def list_stocks(db: AsyncSession) -> list[Stock]:
    result = await db.execute(select(Stock).order_by(Stock.ticker))
    return list(result.scalars().all())


async def get_stock(db: AsyncSession, ticker: str) -> Stock | None:
    return await db.get(Stock, ticker)


async def add_stock(db: AsyncSession, ticker: str) -> Stock:
    obj = Stock(ticker=ticker, price=0)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def remove_stock(db: AsyncSession, ticker: str) -> bool:
    obj = await db.get(Stock, ticker)
    if not obj:
        return False
    await db.delete(obj)
    await db.commit()
    return True


async def get_stock_assets(db: AsyncSession) -> list[Asset]:
    result = await db.execute(
        select(Asset).where(Asset.asset_type == AssetType.stock).order_by(Asset.name)
    )
    return list(result.scalars().all())


def fetch_prices(tickers: list[str]) -> dict[str, float | None]:
    """Fetch current prices for Brazilian stock tickers via yfinance."""
    import yfinance as yf

    prices: dict[str, float | None] = {}
    if not tickers:
        return prices

    # Brazilian tickers on B3 use .SA suffix in yfinance
    yf_tickers = []
    for t in tickers:
        suffix = ".sa" if not t.endswith(".sa") else ""
        yf_tickers.append(f"{t}{suffix}")

    data = yf.download(yf_tickers, period="1d", progress=False, ignore_tz=True)

    if data.empty:
        return {t: None for t in tickers}

    for original, yf_t in zip(tickers, yf_tickers):
        try:
            if len(yf_tickers) == 1:
                price = data["Close"].iloc[-1]
            else:
                price = data["Close"][yf_t.upper()].iloc[-1]
            prices[original] = round(float(price), 2) if price == price else None  # NaN check
        except (KeyError, IndexError):
            prices[original] = None

    return prices


async def update_prices(db: AsyncSession) -> dict[str, float | None]:
    """Update prices for all tracked stocks and stock asset current values."""
    # Gather all tickers: from stocks table + from stock assets
    tracked_stocks = await list_stocks(db)
    stock_assets = await get_stock_assets(db)

    all_tickers: set[str] = set()
    for t in tracked_stocks:
        all_tickers.add(t.ticker)
    for a in stock_assets:
        all_tickers.add(a.name)

    if not all_tickers:
        return {}

    prices = fetch_prices(sorted(all_tickers))

    # Update stocks table
    for t in tracked_stocks:
        if prices.get(t.ticker) is not None:
            t.price = prices[t.ticker]

    # Ensure stock asset tickers exist in stocks table
    for a in stock_assets:
        existing = await db.get(Stock, a.name)
        if not existing and prices.get(a.name) is not None:
            db.add(Stock(ticker=a.name, price=prices[a.name]))

    # Update stock asset current_value = quantity * price
    for a in stock_assets:
        p = prices.get(a.name)
        if p is not None:
            a.current_value = round(float(a.quantity) * p, 2)

    await db.commit()
    return prices
