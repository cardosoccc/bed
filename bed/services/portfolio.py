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
    metric: str = "current"
    total: float = 0.0
    pct: float = 0.0
    target: float = 0.0
    target_pct: float = 0.0
    diff: float = 0.0


@dataclass
class TagRow:
    name: str
    metric: str = "current"
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

    class_current_totals: dict[str, float] = {}
    class_initial_totals: dict[str, float] = {}
    for asset in assets:
        cls = asset.asset_class.value if asset.asset_class else "other"
        class_current_totals[cls] = class_current_totals.get(cls, 0.0) + float(asset.current_value)
        class_initial_totals[cls] = class_initial_totals.get(cls, 0.0) + float(asset.initial_value)

    class_rules: dict[str, Rule] = {}
    for rule in rules:
        if rule.asset_class and not rule.asset_type and not rule.category and not rule.subcategory and not rule.tags:
            class_rules[rule.asset_class] = rule

    all_class_names = sorted(set(class_current_totals.keys()) | set(class_initial_totals.keys()) | set(class_rules.keys()))
    class_rows = [
        _build_row(
            name=name,
            current_total=class_current_totals.get(name, 0.0),
            initial_total=class_initial_totals.get(name, 0.0),
            total_current=total_current,
            total_initial=total_initial,
            rule=class_rules.get(name),
            row_type=ClassRow,
        )
        for name in all_class_names
    ]

    tag_current_totals: dict[str, float] = {}
    tag_initial_totals: dict[str, float] = {}
    for asset in assets:
        if not asset.tags:
            continue
        for tag in asset.tags:
            tag_current_totals[tag] = tag_current_totals.get(tag, 0.0) + float(asset.current_value)
            tag_initial_totals[tag] = tag_initial_totals.get(tag, 0.0) + float(asset.initial_value)

    tag_rules: dict[str, Rule] = {}
    for rule in rules:
        if rule.tags and not rule.asset_class and not rule.asset_type and not rule.category and not rule.subcategory:
            for tag in rule.tags:
                tag_rules[tag] = rule

    all_tag_names = sorted(set(tag_current_totals.keys()) | set(tag_initial_totals.keys()) | set(tag_rules.keys()))
    tag_rows = [
        _build_row(
            name=name,
            current_total=tag_current_totals.get(name, 0.0),
            initial_total=tag_initial_totals.get(name, 0.0),
            total_current=total_current,
            total_initial=total_initial,
            rule=tag_rules.get(name),
            row_type=TagRow,
        )
        for name in all_tag_names
    ]

    return PortfolioStatus(
        assets=assets,
        total_initial=total_initial,
        total_current=total_current,
        classes=class_rows,
        tags=tag_rows,
    )


def _build_row(name, current_total, initial_total, total_current, total_initial, rule, row_type):
    if rule is None:
        pct = (current_total / total_current * 100) if total_current else 0.0
        return row_type(
            name=name,
            metric="current",
            total=current_total,
            pct=pct,
            target=current_total,
            target_pct=pct,
            diff=0.0,
        )

    metric = "current" if rule.current else "invested"
    total = current_total if rule.current else initial_total
    portfolio_total = total_current if rule.current else total_initial
    pct = (total / portfolio_total * 100) if portfolio_total else 0.0
    target, target_pct, diff = _evaluate_rule(rule, total, portfolio_total)
    return row_type(
        name=name,
        metric=metric,
        total=total,
        pct=pct,
        target=target,
        target_pct=target_pct,
        diff=diff,
    )


def _evaluate_rule(rule: Rule, total: float, portfolio_total: float) -> tuple[float, float, float]:
    if rule.target is not None:
        target = _resolve_rule_value(float(rule.target), portfolio_total)
        return target, _to_pct(target, portfolio_total), total - target

    min_value = _resolve_rule_value(float(rule.min), portfolio_total) if rule.min is not None else None
    max_value = _resolve_rule_value(float(rule.max), portfolio_total) if rule.max is not None else None

    if min_value is not None and max_value is not None:
        if total < min_value:
            return min_value, _to_pct(min_value, portfolio_total), total - min_value
        if total > max_value:
            return max_value, _to_pct(max_value, portfolio_total), total - max_value
        return min_value, _to_pct(min_value, portfolio_total), 0.0

    if min_value is not None:
        if total < min_value:
            return min_value, _to_pct(min_value, portfolio_total), total - min_value
        return min_value, _to_pct(min_value, portfolio_total), 0.0

    if max_value is not None:
        if total > max_value:
            return max_value, _to_pct(max_value, portfolio_total), total - max_value
        return max_value, _to_pct(max_value, portfolio_total), 0.0

    return total, _to_pct(total, portfolio_total), 0.0


def _resolve_rule_value(value: float, portfolio_total: float) -> float:
    if 0 <= value <= 1:
        return portfolio_total * value
    return value


def _to_pct(value: float, portfolio_total: float) -> float:
    if not portfolio_total:
        return 0.0
    return value / portfolio_total * 100
