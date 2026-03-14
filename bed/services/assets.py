import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bed.models.asset import Asset
from bed.schemas.asset import AssetCreate, AssetUpdate


async def list_assets(db: AsyncSession) -> list[Asset]:
    result = await db.execute(select(Asset))
    assets = list(result.scalars().all())
    assets.sort(key=lambda a: (a.asset_class.value, sorted(a.tags or []), a.created_at))
    return assets


async def get_asset(db: AsyncSession, asset_id: uuid.UUID) -> Asset | None:
    return await db.get(Asset, asset_id)


async def create_asset(db: AsyncSession, data: AssetCreate) -> Asset:
    asset = Asset(**data.model_dump())
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


async def update_asset(db: AsyncSession, asset_id: uuid.UUID, data: AssetUpdate) -> Asset | None:
    asset = await db.get(Asset, asset_id)
    if not asset:
        return None
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(asset, key, value)
    await db.commit()
    await db.refresh(asset)
    return asset


async def delete_asset(db: AsyncSession, asset_id: uuid.UUID) -> bool:
    asset = await db.get(Asset, asset_id)
    if not asset:
        return False
    await db.delete(asset)
    await db.commit()
    return True
