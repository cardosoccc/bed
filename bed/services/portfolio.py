from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from bed.models.asset import Asset
from bed.models.rule import Rule
from bed.services.assets import list_assets
from bed.services.rules import list_rules


@dataclass
class ClassRow:
    name: str
    total: float = 0.0
    pct: float = 0.0
    target: float = 0.0
    target_pct: float = 0.0
    diff: float = 0.0


@dataclass
class TagRow:
    name: str
    total: float = 0.0
    pct: float = 0.0
    target: float = 0.0
    target_pct: float = 0.0
    diff: float = 0.0


@dataclass
class PortfolioStatus:
    assets: list[Asset] = field(default_factory=list)
    total_initial: float = 0.0
    total_current: float = 0.0
    classes: list[ClassRow] = field(default_factory=list)
    tags: list[TagRow] = field(default_factory=list)


async def get_portfolio_status(db: AsyncSession) -> PortfolioStatus:
    assets = await list_assets(db)
    rules = await list_rules(db)

    total_initial = sum(float(a.initial_value) for a in assets)
    total_current = sum(float(a.current_value) for a in assets)

    # --- class breakdown ---
    class_totals: dict[str, float] = {}
    for a in assets:
        cls = a.asset_class.value if a.asset_class else "other"
        class_totals[cls] = class_totals.get(cls, 0.0) + float(a.current_value)

    class_rules: dict[str, Rule] = {}
    for r in rules:
        if r.asset_class and not r.asset_type and not r.category and not r.subcategory and not r.tags:
            class_rules[r.asset_class] = r

    all_class_names = sorted(set(class_totals.keys()) | set(class_rules.keys()))
    class_rows: list[ClassRow] = []
    for name in all_class_names:
        total = class_totals.get(name, 0.0)
        pct = (total / total_current * 100) if total_current else 0.0
        rule = class_rules.get(name)
        proportion = float(rule.proportion) if rule and rule.proportion is not None else 0.0
        target_pct = proportion * 100
        target = total_current * proportion if proportion else 0.0
        diff = total - target
        class_rows.append(ClassRow(
            name=name, total=total, pct=pct,
            target=target, target_pct=target_pct, diff=diff,
        ))

    # --- tag breakdown ---
    tag_totals: dict[str, float] = {}
    for a in assets:
        if a.tags:
            for tag in a.tags:
                tag_totals[tag] = tag_totals.get(tag, 0.0) + float(a.current_value)

    tag_rules: dict[str, Rule] = {}
    for r in rules:
        if r.tags and not r.asset_class and not r.asset_type and not r.category and not r.subcategory:
            for tag in r.tags:
                tag_rules[tag] = r

    all_tag_names = sorted(set(tag_totals.keys()) | set(tag_rules.keys()))
    tag_rows: list[TagRow] = []
    for name in all_tag_names:
        total = tag_totals.get(name, 0.0)
        pct = (total / total_current * 100) if total_current else 0.0
        rule = tag_rules.get(name)
        proportion = float(rule.proportion) if rule and rule.proportion is not None else 0.0
        target_pct = proportion * 100
        target = total_current * proportion if proportion else 0.0
        diff = total - target
        tag_rows.append(TagRow(
            name=name, total=total, pct=pct,
            target=target, target_pct=target_pct, diff=diff,
        ))

    return PortfolioStatus(
        assets=assets,
        total_initial=total_initial,
        total_current=total_current,
        classes=class_rows,
        tags=tag_rows,
    )
