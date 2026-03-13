import urllib.request
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bed.models.asset import Asset, AssetType
from bed.models.bond import Bond

TESOURO_DIRETO_URLS = [
    "https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/service/api/treasurybondsinfo.json",
    "https://api.radaropcoes.com/bonds.json",
]


def _normalize(name: str) -> str:
    """Normalize a bond name for comparison (collapse hyphens/spaces, strip '+')."""
    return " ".join(name.lower().replace("-", " ").replace("+", "").split())


async def list_bonds(db: AsyncSession) -> list[Bond]:
    result = await db.execute(select(Bond).order_by(Bond.name))
    return list(result.scalars().all())


async def get_bond(db: AsyncSession, name: str) -> Bond | None:
    return await db.get(Bond, name)


async def add_bond(db: AsyncSession, name: str) -> Bond:
    obj = Bond(name=name, price=0)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def remove_bond(db: AsyncSession, name: str) -> bool:
    obj = await db.get(Bond, name)
    if not obj:
        return False
    await db.delete(obj)
    await db.commit()
    return True


async def get_bond_assets(db: AsyncSession) -> list[Asset]:
    result = await db.execute(
        select(Asset).where(Asset.asset_type == AssetType.bond).order_by(Asset.name)
    )
    return list(result.scalars().all())


def _fetch_json(url: str) -> dict | None:
    """Fetch JSON from a URL, returning None on failure."""
    req = urllib.request.Request(url, headers={"User-Agent": "bed-cli/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _parse_prices(data: dict) -> dict[str, float | None]:
    """Parse bond prices from Tesouro Direto API response."""
    prices: dict[str, float | None] = {}
    bond_list = data.get("response", {}).get("TrsrBdTradgList", [])
    for item in bond_list:
        bd = item.get("TrsrBd", {})
        name = bd.get("nm", "").strip()
        red_val = bd.get("untrRedVal")
        if name and red_val is not None:
            prices[name.lower()] = round(float(red_val), 2)
    return prices


def fetch_prices() -> dict[str, float | None]:
    """Fetch current prices for Tesouro Direto bonds.

    Tries multiple API endpoints, falling back to the next on failure.
    Returns a dict mapping lowercased bond name -> unit redemption value (marcação a mercado).
    """
    for url in TESOURO_DIRETO_URLS:
        data = _fetch_json(url)
        if data is not None:
            prices = _parse_prices(data)
            if prices:
                return prices
    return {}


def search_bonds(query: str, available: dict[str, float | None]) -> list[tuple[str, float | None]]:
    """Search available bonds by partial name match."""
    q = query.lower()
    return [(name, price) for name, price in sorted(available.items()) if q in name]


async def update_prices(db: AsyncSession) -> dict[str, float | None]:
    """Update prices for all tracked bonds and bond asset current values."""
    tracked_bonds = await list_bonds(db)
    bond_assets = await get_bond_assets(db)

    all_names: set[str] = set()
    for b in tracked_bonds:
        all_names.add(b.name)
    for a in bond_assets:
        all_names.add(a.name)

    if not all_names:
        return {}

    api_prices = fetch_prices()
    if not api_prices:
        return {name: None for name in all_names}

    # Build a normalized lookup: normalized_name -> price
    norm_lookup: dict[str, float] = {}
    for api_name, price in api_prices.items():
        norm_lookup[_normalize(api_name)] = price

    prices: dict[str, float | None] = {}
    for name in all_names:
        exact = api_prices.get(name)
        prices[name] = exact if exact is not None else norm_lookup.get(_normalize(name))

    # Update bonds table
    for b in tracked_bonds:
        if prices.get(b.name) is not None:
            b.price = prices[b.name]

    # Ensure bond asset names exist in bonds table
    for a in bond_assets:
        existing = await db.get(Bond, a.name)
        if not existing and prices.get(a.name) is not None:
            db.add(Bond(name=a.name, price=prices[a.name]))

    # Update bond asset current_value = quantity * price
    for a in bond_assets:
        p = prices.get(a.name)
        if p is not None:
            a.current_value = round(float(a.quantity) * p, 2)

    await db.commit()
    return prices
