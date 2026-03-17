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


def _compute_diff(total: float, pct: float, total_current: float, rule: Rule | None):
    """Compute target, target_pct, and diff for a given total against a rule.

    Logic:
    - No rule: target = total, diff = 0
    - Rule with current_value (absolute target): diff = total - current_value
    - Rule with proportion (target proportion):
      - If min/max proportions are set, diff is relative to the band:
        - Within band → diff = 0
        - Below min → diff = total - min_value
        - Above max → diff = total - max_value
      - Otherwise diff = total - target
    """
    if rule is None:
        return total, pct, 0.0

    if rule.current_value is not None:
        target = float(rule.current_value)
        target_pct = (target / total_current * 100) if total_current else 0.0
        diff = total - target
        return target, target_pct, diff

    proportion = float(rule.proportion) if rule.proportion is not None else 0.0
    target_pct = proportion * 100
    target = total_current * proportion if proportion else 0.0

    min_prop = float(rule.min_proportion) if rule.min_proportion is not None else None
    max_prop = float(rule.max_proportion) if rule.max_proportion is not None else None

    if min_prop is not None or max_prop is not None:
        min_val = total_current * min_prop if min_prop is not None else None
        max_val = total_current * max_prop if max_prop is not None else None

        if min_val is not None and max_val is not None:
            if total < min_val:
                diff = total - min_val
            elif total > max_val:
                diff = total - max_val
            else:
                diff = 0.0
        elif min_val is not None:
            diff = total - min_val if total < min_val else 0.0
        else:
            diff = total - max_val if total > max_val else 0.0
    else:
        diff = total - target

    return target, target_pct, diff


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
        target, target_pct, diff = _compute_diff(total, pct, total_current, rule)
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
        target, target_pct, diff = _compute_diff(total, pct, total_current, rule)
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
