---
title: feat: Add target/min/max rule semantics for portfolio status
type: feat
status: completed
date: 2026-04-01
deepened: 2026-04-01
---

# feat: Add target/min/max rule semantics for portfolio status

## Overview

Replace the current `proportion` / `current_value` split with one bounded rule model: a rule may define `target`, `min`, `max`, or `min`+`max`, with `target` mutually exclusive with bounds. Any `target`, `min`, or `max` value between `0` and `1` inclusive is interpreted as a portfolio percentage; values above `1` are interpreted as absolute amounts. Portfolio diffs should then reflect whether a portfolio slice is outside the allowed range instead of always using `total - target`.

## Problem Frame

Today the rule model exposes `proportion`, `invested_value`, and `current_value`, but the status report only understands two cases: exact `current_value` targets or `proportion` targets. This splits one concept across two fields, forces value-based rules into exact-match behavior, and makes `diff` misleading for cases where the desired behavior is “at least X”, “at most Y”, or “stay between X and Y”.

The requested behavior is:

- `target` only: keep exact-target semantics, and `diff = total - resolved_target`
- `min` only: values below `resolved_min` produce a negative diff; values at or above `resolved_min` produce `0`
- `max` only: values above `resolved_max` produce a positive diff; values at or below `resolved_max` produce `0`
- `min` + `max`: values inside the resolved range produce `0`; below range produces a negative diff; above range produces a positive diff
- `target` cannot coexist with `min` and/or `max`
- `target`, `min`, and `max` values in the inclusive range `0..1` are interpreted as percentages of total current portfolio value
- `target`, `min`, and `max` values greater than `1` are interpreted as absolute amounts
- there is no separate `proportion` field anymore

## Requirements Trace

- R1. Rules must support threshold semantics of `target`, `min`, `max`, or `min`+`max`.
- R2. `target` must be mutually exclusive with `min` and `max` during create and edit flows.
- R3. `target`, `min`, and `max` must resolve as percentages when their stored values are between `0` and `1` inclusive, and as absolute amounts otherwise.
- R4. `bed pp` must compute diff according to the selected rule mode instead of always subtracting from a single target.
- R5. Rule CRUD, storage, and docs must expose the new contract clearly enough that users can create and inspect bounded rules without guessing.
- R6. Existing percentage-target behavior must be preserved through `target` values in `0..1`, even though the dedicated `proportion` field is removed.
- R7. The implementation plan must preserve the repo’s test-first posture by naming the failing tests to add before code changes.

## Scope Boundaries

- In scope: current-value rule semantics used by [bed/services/portfolio.py](/home/ccc/wrk/prj/bed/bed/services/portfolio.py) and surfaced via [bed/commands/db_commands.py](/home/ccc/wrk/prj/bed/bed/commands/db_commands.py).
- In scope: rule persistence, schemas, CLI options, list output, migration support, and docs for the new current-value rule contract.
- Out of scope: changing asset aggregation dimensions beyond the current class/tag breakdowns.
- Out of scope: adding new reporting for invested-value rules. Assumption for this plan: `invested_value` remains unchanged unless explicitly expanded in a follow-up.
- Out of scope: supporting percentage values outside `0..1`; those are treated as absolute amounts by design.

## Context & Research

### Relevant Code and Patterns

- [bed/models/rule.py](/home/ccc/wrk/prj/bed/bed/models/rule.py) stores the current rule shape and is the only ORM model affected by this change.
- [bed/schemas/rule.py](/home/ccc/wrk/prj/bed/bed/schemas/rule.py) already centralizes rule create/update/read payloads, so validation and percentage-vs-absolute interpretation rules should live here or in closely-related service helpers instead of being duplicated in commands and services.
- [bed/commands/rules.py](/home/ccc/wrk/prj/bed/bed/commands/rules.py) follows the project’s direct Click-option pattern and is the public CLI contract for rule CRUD.
- [bed/services/portfolio.py](/home/ccc/wrk/prj/bed/bed/services/portfolio.py) computes class/tag totals and currently hard-codes exact-target diff logic for both class- and tag-scoped rules.
- [bed/database.py](/home/ccc/wrk/prj/bed/bed/database.py) uses additive SQLite migrations via `_add_column_if_missing`, so schema evolution should follow that pattern instead of introducing a migration framework.
- [tests/test_rules_service.py](/home/ccc/wrk/prj/bed/tests/test_rules_service.py), [tests/test_rules_command.py](/home/ccc/wrk/prj/bed/tests/test_rules_command.py), [tests/test_portfolio_service.py](/home/ccc/wrk/prj/bed/tests/test_portfolio_service.py), and [tests/test_portfolio_status_command.py](/home/ccc/wrk/prj/bed/tests/test_portfolio_status_command.py) already cover the affected seams.

### Institutional Learnings

- No `docs/solutions/` directory exists in this repo, so there are no stored institutional learnings to carry forward.

### External References

- Skipped. The repo already has strong local patterns for CLI option handling, SQLite additive migrations, and portfolio-status test coverage. This change is primarily a repo-specific contract evolution, not a framework-behavior question.

## Key Technical Decisions

- Replace `proportion` and the single current-value constraint with explicit fields such as `target`, `min`, and `max`.
  Rationale: the user wants one unified rule model where stored numbers can mean either percentages or absolute values depending on range; a separate `proportion` field would keep the old split alive.
- Keep validation in Pydantic rule schemas rather than only in Click commands.
  Rationale: service tests, command tests, and any future non-CLI callers all benefit from one source of truth for “target xor bounds”.
- Extract portfolio diff calculation into a small helper in [bed/services/portfolio.py](/home/ccc/wrk/prj/bed/bed/services/portfolio.py).
  Rationale: class and tag paths currently duplicate the same branching and will otherwise duplicate both the new range logic and the percentage-resolution logic.
- Interpret stored values in `0..1` inclusive as percentages of total current portfolio value.
  Rationale: this preserves the current percentage authoring ergonomics while removing the need for a dedicated `proportion` field.
- Use an additive migration path that introduces the new unified fields and migrates legacy `proportion` / `current_value` data forward.
  Rationale: the project already supports lightweight migrations and may need to preserve old databases while code shifts over.

## Open Questions

### Resolved During Planning

- Should this plan change `bed pp` diff semantics for both class and tag rule rows?
  Resolution: yes. Both flows share the same rule model and currently mirror each other in [bed/services/portfolio.py](/home/ccc/wrk/prj/bed/bed/services/portfolio.py).
- Should existing percentage rules keep exact-target diff behavior after removing `proportion`?
  Resolution: yes. Existing percentage behavior moves under `target` values in `0..1`, so diff behavior stays exact-target after value resolution.

### Deferred to Implementation

- Whether the legacy `proportion` and `current_value` columns should be dropped immediately or preserved temporarily after forward-migrating their data into `target`.
  Deferred because the correct choice depends on how conservative the implementation wants to be with existing local databases and backwards compatibility.
- How the status table should label the rule columns for bound-only rows.
  Deferred because the implementation can validate the best presentation once the new row data shape exists, but it must remain explicit and test-covered.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

| Rule mode | Allowed fields | Status diff formula | Expected sign |
|---|---|---|---|
| Exact target | `target` | `total - resolved_target` | negative below target, positive above |
| Minimum only | `min` | `total - resolved_min` when `total < resolved_min`, else `0` | negative only |
| Maximum only | `max` | `total - resolved_max` when `total > resolved_max`, else `0` | positive only |
| Range | `min`, `max` | `total - resolved_min` when below range; `0` inside range; `total - resolved_max` when above range | negative below, positive above |

Resolution rule:

- if stored value is between `0` and `1` inclusive, resolve it as `total_current * stored_value`
- if stored value is greater than `1`, resolve it as the stored absolute amount

Validation matrix:

- allowed: `target`
- allowed: `min`
- allowed: `max`
- allowed: `min` + `max`
- rejected: `target` + `min`
- rejected: `target` + `max`
- rejected: `target` + `min` + `max`

## Implementation Units

- [x] **Unit 1: Redesign the rule schema and persistence contract**

**Goal:** Introduce unified `target` / `min` / `max` rule fields, remove `proportion`, and centralize validation plus legacy-data migration.

**Requirements:** R1, R2, R3, R5, R6

**Dependencies:** None

**Files:**
- Modify: `bed/models/rule.py`
- Modify: `bed/schemas/rule.py`
- Modify: `bed/database.py`
- Modify: `bed/migrate.py`
- Test: `tests/test_rules_service.py`

**Approach:**
- Add explicit ORM/schema fields for the new unified modes and remove `proportion` from the active contract.
- Add schema-level validation that enforces `target` xor bounds and rejects empty bound rules.
- Extend the lightweight migration path so existing SQLite databases gain the new columns safely.
- Forward-map legacy `proportion` rows into `target` percentage values and legacy `current_value` rows into `target` absolute values.
- Decide during implementation whether old columns remain temporarily for compatibility or are cleaned up after migration.

**Execution note:** Start with failing schema/service tests that prove the accepted and rejected field combinations before changing persistence code.

**Patterns to follow:**
- Additive migration helpers in [bed/database.py](/home/ccc/wrk/prj/bed/bed/database.py)
- CRUD service coverage style in [tests/test_rules_service.py](/home/ccc/wrk/prj/bed/tests/test_rules_service.py)

**Test scenarios:**
- Happy path: creating a rule with only `target=0.60` persists a percentage target and leaves bounds empty.
- Happy path: creating a rule with only `target=6000` persists an absolute target.
- Happy path: creating a rule with only `min=0.20` persists a percentage minimum-only rule.
- Happy path: creating a rule with only `max=5000` persists an absolute maximum-only rule.
- Happy path: creating a rule with both `min=0.10` and `max=0.30` persists a percentage range rule.
- Happy path: creating a rule with both `min=1000` and `max=3000` persists an absolute range rule.
- Edge case: updating an existing target rule into a range rule clears the target field and stores both bounds.
- Edge case: updating an existing range rule into a target rule clears both bounds and stores only target.
- Error path: creating a rule with `target` plus `min` is rejected with a validation error.
- Error path: creating a rule with `target` plus `max` is rejected with a validation error.
- Integration: migrating an older database maps legacy `proportion` data into `target` and preserves rule retrieval.
- Integration: migrating an older database maps legacy `current_value` data into `target` and preserves rule retrieval.

**Verification:**
- Rule create/update paths can represent all four requested modes and reject invalid combinations consistently through the schema layer.

- [x] **Unit 2: Update the rule CLI contract and inspectability**

**Goal:** Make `bed rule create`, `bed rule edit`, and `bed rule list` expose the new value-rule modes clearly.

**Requirements:** R2, R3, R5

**Dependencies:** Unit 1

**Files:**
- Modify: `bed/commands/rules.py`
- Modify: `README.md`
- Modify: `skills/bed/SKILL.md`
- Test: `tests/test_rules_command.py`

**Approach:**
- Replace `--proportion` and the single current-value option with explicit `--target`, `--min`, and `--max` options.
- Keep aliases and one-word CLI conventions intact.
- Update list output so a user can tell whether a rule is exact, minimum-only, maximum-only, or ranged, and whether each stored value will act like a percentage or an absolute amount.
- Refresh README and skill examples so they stop advertising `--proportion` and the old single-value contract.

**Execution note:** Add CLI tests first, especially for invalid option combinations and list output, before modifying Click command wiring.

**Patterns to follow:**
- Click option style in [bed/commands/rules.py](/home/ccc/wrk/prj/bed/bed/commands/rules.py)
- Integration-style CLI tests in [tests/test_rules_command.py](/home/ccc/wrk/prj/bed/tests/test_rules_command.py)

**Test scenarios:**
- Happy path: `rule create --target 0.60` accepts a percentage target and reports successful creation.
- Happy path: `rule create --target 6000` accepts an absolute target and reports successful creation.
- Happy path: `rule create --min 0.20` accepts a percentage minimum-only rule and reports successful creation.
- Happy path: `rule create --max 5000` accepts an absolute maximum-only rule and reports successful creation.
- Happy path: `rule create --min 0.10 --max 0.30` accepts a percentage range rule and reports successful creation.
- Edge case: `rule edit` can convert an existing target rule into a min-only rule.
- Error path: `rule create` with target plus min exits non-zero or prints a validation error and does not persist the rule.
- Error path: `rule edit` with target plus max exits non-zero or prints a validation error and does not mutate the rule.
- Integration: `rule create --target 0.60` no longer relies on `--proportion`; the old option is removed from the public contract.
- Integration: `rule list` output makes the active rule mode visible for each row.

**Verification:**
- A user can create, edit, and list all supported rule modes from the CLI without needing undocumented field knowledge.

- [x] **Unit 3: Rework portfolio diff evaluation around bounded rules**

**Goal:** Make class/tag status rows resolve `target` / `min` / `max` as percentage-or-absolute values and compute `diff` according to exact-target, min-only, max-only, or range semantics.

**Requirements:** R1, R3, R4, R6

**Dependencies:** Unit 1

**Files:**
- Modify: `bed/services/portfolio.py`
- Test: `tests/test_portfolio_service.py`

**Approach:**
- Extract shared rule-evaluation logic so class rows and tag rows use the same branch table.
- Preserve existing no-rule behavior (`diff = 0`) and existing percentage-target behavior by resolving `target=0..1` against total current portfolio value.
- When a value rule is bound-based, return zero diff for in-range totals and signed overflow/underflow outside the allowed range.
- Keep row ordering and existing class/tag aggregation behavior unchanged.

**Execution note:** Implement new portfolio service tests first; they are the clearest expression of the requested diff semantics.

**Technical design:** *(Directional guidance, not implementation specification.)* A small evaluator should accept `(row_total, total_current, rule)`, resolve each stored bound into an absolute amount based on the `0..1` percentage rule, and return the rendered target/rule metadata plus `diff`, so the class and tag loops stop owning rule-mode branching directly.

**Patterns to follow:**
- Existing class/tag symmetry in [bed/services/portfolio.py](/home/ccc/wrk/prj/bed/bed/services/portfolio.py)
- Portfolio behavior assertions in [tests/test_portfolio_service.py](/home/ccc/wrk/prj/bed/tests/test_portfolio_service.py)

**Test scenarios:**
- Happy path: a `target=0.60` rule still yields the same percentage-based target amount and `diff` as the old `proportion=0.60` rule.
- Happy path: a `target=6000` rule yields `diff = total - 6000`.
- Happy path: a min-only class rule with `min=0.20` yields a negative diff when total is below the resolved percentage minimum.
- Happy path: a min-only class rule yields zero diff when total equals the minimum.
- Happy path: a max-only tag rule with `max=0.25` yields a positive diff when total is above the resolved percentage maximum.
- Happy path: a max-only tag rule yields zero diff when total is below the maximum.
- Happy path: a min+max rule yields zero diff when total is inside the range.
- Edge case: a min+max rule yields a negative diff when total is below the lower bound.
- Edge case: a min+max rule yields a positive diff when total is above the upper bound.
- Edge case: a rule-only class with no assets still shows the correct signed diff against its bound.
- Integration: migrated legacy `proportion` rows still produce the same target and diff values as before once read through `target`.

**Verification:**
- Portfolio service rows reflect the requested sign rules exactly and retain existing behavior for no-rule and legacy percentage-target rows.

- [x] **Unit 4: Adapt the portfolio status output contract and docs**

**Goal:** Ensure `bed portfolio status` / `bed pp` renders the new rule semantics in a way users can interpret from the table output.

**Requirements:** R3, R4, R5

**Dependencies:** Unit 2, Unit 3

**Files:**
- Modify: `bed/commands/db_commands.py`
- Modify: `README.md`
- Test: `tests/test_portfolio_status_command.py`

**Approach:**
- Decide on the least confusing report shape for bound-aware rows, then apply it consistently to both Classes and Tags tables.
- Keep the report width, separators, aliases, and overall multi-table format intact.
- Update command-level tests to assert the rendered contract for target, min-only, max-only, and range rows, including percentage-authored rules.

**Execution note:** Start with command tests that lock the intended `pp` rendering for each rule mode before changing the tabular output.

**Patterns to follow:**
- Existing report formatting in [bed/commands/db_commands.py](/home/ccc/wrk/prj/bed/bed/commands/db_commands.py)
- Status command integration tests in [tests/test_portfolio_status_command.py](/home/ccc/wrk/prj/bed/tests/test_portfolio_status_command.py)

**Test scenarios:**
- Happy path: `pp` shows a `target=0.60` row with the resolved target amount, percentage meaning, and expected diff.
- Happy path: `pp` shows a `target=6000` row with the expected diff and visible target metadata.
- Happy path: `pp` shows a min-only row where an in-range value renders diff `0.00`.
- Happy path: `pp` shows a max-only row where an above-range value renders a positive diff.
- Happy path: `pp` shows a min+max row where an in-range value renders diff `0.00`.
- Edge case: `pp` shows a min+max row below range with a negative diff.
- Edge case: `pp` shows a min+max row above range with a positive diff.
- Integration: migrated legacy percentage rules still appear correctly after the `proportion` field is removed from the public contract.
- Integration: existing output structure still includes Assets, Classes, Tags, separator width, and alias coverage.

**Verification:**
- `bed pp` makes each rule mode and resulting diff understandable from the rendered tables, not only from internal storage.

## System-Wide Impact

- **Interaction graph:** rule create/edit/list, portfolio status service evaluation, and portfolio status CLI rendering all change together; partial rollout would produce mismatched storage and display behavior.
- **Error propagation:** invalid rule combinations should fail at schema validation and surface through CLI command output without persisting partial updates.
- **State lifecycle risks:** schema evolution for existing SQLite databases is the main persistent-state risk; legacy `proportion` and `current_value` rows must remain readable after migration into the unified contract.
- **API surface parity:** both full commands (`rule create`, `portfolio status`) and aliases (`r c`, `pp`) must continue to behave consistently.
- **Integration coverage:** command tests must prove that persisted rules are rendered correctly in `pp`, not just that the service computes the right numeric diff.
- **Unchanged invariants:** asset CRUD, aggregation dimensions, and no-rule status rows should retain current behavior; legacy percentage rules should preserve behavior through the new `target` field.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Ambiguous `pp` table presentation for min/max rows could confuse users even if diff math is correct | Lock the output contract with command tests and update README examples in the same change |
| Existing local databases may still contain `proportion` and `current_value` rows | Use additive migration and migrate both legacy fields forward into `target`, with compatibility handling during rollout if cleanup is deferred |
| Percentage-vs-absolute interpretation may be surprising around the `1.0` boundary | Lock the `0..1 inclusive = percentage` rule in schema, service, command, and status tests so boundary behavior is intentional and documented |
| Validation might drift between schemas and CLI options | Keep the canonical mutual-exclusion logic in [bed/schemas/rule.py](/home/ccc/wrk/prj/bed/bed/schemas/rule.py) and keep CLI tests focused on surfaced behavior |
| Class and tag logic could diverge if the evaluator is duplicated | Centralize the rule-mode evaluation helper inside [bed/services/portfolio.py](/home/ccc/wrk/prj/bed/bed/services/portfolio.py) |

## Documentation / Operational Notes

- Update README examples away from `--proportion` and toward unified `--target`, `--min`, and `--max`.
- Update [skills/bed/SKILL.md](/home/ccc/wrk/prj/bed/skills/bed/SKILL.md) so future agent-driven usage follows the new CLI contract.
- If the implementation keeps legacy `proportion` / `current_value` compatibility paths, document their temporary nature in code comments or README notes to avoid long-term dual-contract drift.

## Sources & References

- Related code: [bed/models/rule.py](/home/ccc/wrk/prj/bed/bed/models/rule.py)
- Related code: [bed/schemas/rule.py](/home/ccc/wrk/prj/bed/bed/schemas/rule.py)
- Related code: [bed/commands/rules.py](/home/ccc/wrk/prj/bed/bed/commands/rules.py)
- Related code: [bed/services/portfolio.py](/home/ccc/wrk/prj/bed/bed/services/portfolio.py)
- Related code: [bed/commands/db_commands.py](/home/ccc/wrk/prj/bed/bed/commands/db_commands.py)
- Related tests: [tests/test_rules_service.py](/home/ccc/wrk/prj/bed/tests/test_rules_service.py)
- Related tests: [tests/test_rules_command.py](/home/ccc/wrk/prj/bed/tests/test_rules_command.py)
- Related tests: [tests/test_portfolio_service.py](/home/ccc/wrk/prj/bed/tests/test_portfolio_service.py)
- Related tests: [tests/test_portfolio_status_command.py](/home/ccc/wrk/prj/bed/tests/test_portfolio_status_command.py)
