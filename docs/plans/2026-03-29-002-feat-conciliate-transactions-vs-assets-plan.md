---
title: "feat: Conciliate command to compare transaction positions vs assets"
type: feat
status: completed
date: 2026-03-29
---

# feat: Conciliate command to compare transaction positions vs assets

## Overview

Add a `bed conciliate` command that consolidates all buy/sell transactions by ticker to compute net positions, then compares against the `assets` table to report discrepancies. Output-only (no auto-fix).

## Problem Statement

Asset quantities and values are manually maintained in the `assets` table. Transaction history (imported via `bed t i`) tracks every buy/sell but is not linked to assets. There is no way to verify that asset records match what the transaction history says the current position should be.

## Proposed Solution

### CLI Interface

```bash
bed conciliate          # compare transaction positions vs assets
bed conciliate -v       # verbose: show all positions, not just discrepancies
```

Aliases: `bed c` (single-letter — currently unused), or keep under a group.

### Algorithm

1. **Query all buy/sell transactions** — types `Compra` and `Venda`
2. **Consolidate by ticker** — for each ticker:
   - Sum quantities: `+qty` for Compra, `-qty` for Venda
   - Sum total_value (already signed: positive for Compra, negative for Venda)
   - Compute average buy price = total bought value / total bought qty
3. **Filter to active positions** — net quantity > 0
4. **Load all assets** from assets table
5. **Match** — join on `Transaction.ticker == Asset.name`
6. **Report discrepancies**:
   - Positions in transactions but **not in assets** (missing asset)
   - Assets that have **no matching transactions** (orphan asset)
   - Quantity mismatch (transaction net qty != asset qty)

### Output Format

```
conciliation report
====================

discrepancies:

  ticker    txn_qty    asset_qty  status
--------  ---------  -----------  ----------------
  PETR4        300          200   qty mismatch
  CSAN3       2600            -   missing asset
  BBDC4          -          100   no transactions

summary: 2 mismatches, 1 missing asset, 1 orphan asset

(use -v to show all positions including matches)
```

With `--verbose`:

```
  ticker    txn_qty    asset_qty  status
--------  ---------  -----------  --------
  BBAS3        400          400   ok
  PETR4        300          200   mismatch
  ...
```

## Technical Considerations

### Matching Logic

- **Stocks**: `Transaction.ticker` == `Asset.name` (both store e.g. "PETR4")
- **Bonds/CDBs**: `Transaction.ticker` is NULL. These won't match and should be skipped or handled separately (out of scope for MVP — focus on stocks where ticker is available)
- **Asset types**: Only compare against assets with `asset_type` in (`stock`, `etf`, `reit`, `fund`) — skip `bond` and `other`

### Sign Convention

Transactions use:
- `quantity` is always positive (absolute value)
- `type == "Compra"` → bought shares (add to position)
- `type == "Venda"` → sold shares (subtract from position)
- `total_value` is positive for buys, negative for sells

### Architecture

New files:
- `bed/services/conciliate.py` — consolidation + comparison logic
- `bed/commands/conciliate.py` — CLI command

Register in `bed/cli.py` with alias.

## Acceptance Criteria

- [ ] `bed conciliate` shows discrepancies between transaction positions and assets
- [ ] Consolidates Compra/Venda transactions by ticker to compute net quantity
- [ ] Only reports positions with net qty > 0 (active positions)
- [ ] Reports: missing assets, orphan assets, quantity mismatches
- [ ] `--verbose` flag shows all positions including matches
- [ ] Summary line with counts
- [ ] Skips tickers that are NULL (bonds/CDBs)
- [ ] Unit tests for consolidation logic
- [ ] Integration test for CLI command

## Implementation

### `bed/services/conciliate.py`

```python
async def consolidate_positions(db) -> dict[str, Position]:
    """Query all Compra/Venda transactions, group by ticker, return net positions."""

async def conciliate(db) -> ConciliationReport:
    """Compare consolidated positions against assets, return report."""
```

`Position` dataclass: `ticker`, `quantity`, `avg_price`, `total_invested`
`ConciliationReport` dataclass: `matches`, `mismatches`, `missing_assets`, `orphan_assets`

### `bed/commands/conciliate.py`

```python
@click.command("conciliate")
@click.option("--verbose", "-v", is_flag=True)
def conciliate_cmd(verbose): ...
```

### `bed/cli.py`

Register `conciliate_cmd`, add alias `c`.

## Sources

- Asset model: `bed/models/asset.py`
- Transaction model: `bed/models/transaction.py`
- Asset service: `bed/services/assets.py`
- Transaction service: `bed/services/transactions.py`
- CLI patterns: `bed/cli.py`, `bed/commands/assets.py`
