import csv
import io
import urllib.request
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bed.models.asset import Asset, AssetType
from bed.models.bond import Bond

TESOURO_DIRETO_JSON_URL = (
    "https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/service/api/treasurybondsinfo.json"
)

TESOURO_DIRETO_CSV_URL = (
    "https://www.tesourodireto.com.br/documents/d/guest/rendimento-resgatar-csv?download=true"
)

TESOURO_TRANSPARENTE_CSV_URL = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/"
    "df56aa42-484a-4a59-8184-7676580c81e3/resource/"
    "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PresseuTD.csv"
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html,text/csv,*/*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


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


def _fetch_url(url: str, timeout: int = 30) -> bytes | None:
    """Fetch a URL and return the response body, or None on failure."""
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None


def _parse_json_api(raw: bytes) -> dict[str, float]:
    """Parse the official Tesouro Direto JSON API response."""
    prices: dict[str, float] = {}
    try:
        data = json.loads(raw.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return prices

    bond_list = data.get("response", {}).get("TrsrBdTradgList", [])
    for item in bond_list:
        bd = item.get("TrsrBd", {})
        name = bd.get("nm", "").strip()
        red_val = bd.get("untrRedVal")
        if name and red_val is not None:
            prices[name.lower()] = round(float(red_val), 2)

    return prices


def _parse_csv_resgatar(raw: bytes) -> dict[str, float]:
    """Parse the Tesouro Direto CSV (rendimento-resgatar) format.

    Expected columns (semicolon-separated):
    Título;Vencimento;Taxa(%);Preço Unitário
    """
    prices: dict[str, float] = {}
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("latin-1")
        except UnicodeDecodeError:
            return prices

    reader = csv.reader(io.StringIO(text), delimiter=";")
    header = None
    for row in reader:
        if not row:
            continue
        if header is None:
            header = [col.strip().lower() for col in row]
            continue
        if len(row) < len(header):
            continue

        row_dict = dict(zip(header, [col.strip() for col in row]))

        name = ""
        for key in ("título", "titulo", "nome"):
            if key in row_dict:
                name = row_dict[key]
                break
        if not name:
            # try first column as name
            name = row[0].strip()

        price_str = ""
        for key in ("preço unitário", "preco unitario", "pu", "preço"):
            if key in row_dict:
                price_str = row_dict[key]
                break
        if not price_str:
            # try last column
            price_str = row[-1].strip()

        if name and price_str:
            try:
                price = float(price_str.replace(".", "").replace(",", "."))
                prices[name.lower()] = round(price, 2)
            except ValueError:
                continue

    return prices


def _parse_tesouro_transparente_csv(raw: bytes) -> dict[str, float]:
    """Parse the Tesouro Transparente historical CSV.

    This CSV contains historical data; we extract the latest price per bond.
    Expected columns (semicolon-separated):
    Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha;PU Venda Manha;PU Base Manha
    """
    prices: dict[str, float] = {}
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("latin-1")
        except UnicodeDecodeError:
            return prices

    reader = csv.reader(io.StringIO(text), delimiter=";")
    header = None
    # Track latest date per bond for most recent price
    latest: dict[str, tuple[str, float]] = {}

    for row in reader:
        if not row:
            continue
        if header is None:
            header = [col.strip().lower() for col in row]
            continue
        if len(row) < len(header):
            continue

        row_dict = dict(zip(header, [col.strip() for col in row]))

        bond_type = row_dict.get("tipo titulo", "").strip()
        maturity = row_dict.get("data vencimento", "").strip()
        date = row_dict.get("data base", "").strip()

        # PU Venda Manha is the mark-to-market redemption price
        pu_str = row_dict.get("pu venda manha", "") or row_dict.get("pu base manha", "")
        pu_str = pu_str.strip()

        if not (bond_type and date and pu_str):
            continue

        # Build the bond name like "tesouro selic 2029"
        year = maturity.split("/")[-1] if "/" in maturity else maturity[-4:]
        name = f"{bond_type} {year}".lower()

        try:
            pu = float(pu_str.replace(".", "").replace(",", "."))
        except ValueError:
            continue

        existing = latest.get(name)
        if existing is None or date > existing[0]:
            latest[name] = (date, round(pu, 2))

    for name, (_, pu) in latest.items():
        prices[name] = pu

    return prices


def fetch_prices() -> dict[str, float | None]:
    """Fetch current prices for Tesouro Direto bonds.

    Tries multiple sources with fallback:
    1. Official Tesouro Direto JSON API (real-time)
    2. Tesouro Direto CSV export (redemption values)
    3. Tesouro Transparente CSV (government open data, historical)

    Returns a dict mapping lowercased bond name -> unit redemption value (marcação a mercado).
    """
    # Source 1: Official JSON API
    raw = _fetch_url(TESOURO_DIRETO_JSON_URL)
    if raw:
        prices = _parse_json_api(raw)
        if prices:
            return prices

    # Source 2: CSV from tesourodireto.com.br
    raw = _fetch_url(TESOURO_DIRETO_CSV_URL)
    if raw:
        prices = _parse_csv_resgatar(raw)
        if prices:
            return prices

    # Source 3: Tesouro Transparente (government open data)
    raw = _fetch_url(TESOURO_TRANSPARENTE_CSV_URL)
    if raw:
        prices = _parse_tesouro_transparente_csv(raw)
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
