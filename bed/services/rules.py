import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bed.models.rule import Rule
from bed.schemas.rule import RuleCreate, RuleUpdate


async def list_rules(db: AsyncSession) -> list[Rule]:
    result = await db.execute(select(Rule).order_by(Rule.description))
    return list(result.scalars().all())


async def get_rule(db: AsyncSession, rule_id: uuid.UUID) -> Rule | None:
    return await db.get(Rule, rule_id)


async def create_rule(db: AsyncSession, data: RuleCreate) -> Rule:
    rule = Rule(**data.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def update_rule(db: AsyncSession, rule_id: uuid.UUID, data: RuleUpdate) -> Rule | None:
    rule = await db.get(Rule, rule_id)
    if not rule:
        return None
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(rule, key, value)
    await db.commit()
    await db.refresh(rule)
    return rule


async def delete_rule(db: AsyncSession, rule_id: uuid.UUID) -> bool:
    rule = await db.get(Rule, rule_id)
    if not rule:
        return False
    await db.delete(rule)
    await db.commit()
    return True
