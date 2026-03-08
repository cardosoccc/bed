import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def resolve_asset_id(db: AsyncSession, identifier: str) -> uuid.UUID | None:
    from bed.models.asset import Asset

    try:
        return uuid.UUID(identifier)
    except ValueError:
        pass

    try:
        idx = int(identifier)
        result = await db.execute(select(Asset).order_by(Asset.name))
        assets = list(result.scalars().all())
        if 1 <= idx <= len(assets):
            return assets[idx - 1].id
        return None
    except ValueError:
        pass

    result = await db.execute(select(Asset).where(Asset.name == identifier))
    asset = result.scalars().first()
    return asset.id if asset else None



async def resolve_rule_id(db: AsyncSession, identifier: str) -> uuid.UUID | None:
    from bed.models.rule import Rule

    try:
        return uuid.UUID(identifier)
    except ValueError:
        pass

    try:
        idx = int(identifier)
        result = await db.execute(select(Rule).order_by(Rule.description))
        rules = list(result.scalars().all())
        if 1 <= idx <= len(rules):
            return rules[idx - 1].id
        return None
    except ValueError:
        pass

    result = await db.execute(select(Rule).where(Rule.description == identifier))
    rule = result.scalars().first()
    return rule.id if rule else None
