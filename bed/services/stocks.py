from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bed.models.asset import Asset, AssetType
from bed.models.ticker import Ticker


async def list_tickers(db: AsyncSession) -> list[Ticker]:
    result = await db.execute(select(Ticker).order_by(Ticker.ticker))
    return list(result.scalars().all())


async def get_ticker(db: AsyncSession, ticker: str) -> Ticker | None:
    return await db.get(Ticker, ticker)


async def add_ticker(db: AsyncSession, ticker: str) -> Ticker:
    obj = Ticker(ticker=ticker, price=0)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def remove_ticker(db: AsyncSession, ticker: str) -> bool:
    obj = await db.get(Ticker, ticker)
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
    """Update prices for all tickers of interest and stock asset current values."""
    # Gather all tickers: from ticker table + from stock assets
    tickers_of_interest = await list_tickers(db)
    stock_assets = await get_stock_assets(db)

    all_tickers: set[str] = set()
    for t in tickers_of_interest:
        all_tickers.add(t.ticker)
    for a in stock_assets:
        all_tickers.add(a.name)

    if not all_tickers:
        return {}

    prices = fetch_prices(sorted(all_tickers))

    # Update ticker table
    for t in tickers_of_interest:
        if prices.get(t.ticker) is not None:
            t.price = prices[t.ticker]

    # Ensure stock asset tickers exist in ticker table
    for a in stock_assets:
        existing = await db.get(Ticker, a.name)
        if not existing and prices.get(a.name) is not None:
            db.add(Ticker(ticker=a.name, price=prices[a.name]))

    # Update stock asset current_value = quantity * price
    for a in stock_assets:
        p = prices.get(a.name)
        if p is not None:
            a.current_value = round(float(a.quantity) * p, 2)

    await db.commit()
    return prices
