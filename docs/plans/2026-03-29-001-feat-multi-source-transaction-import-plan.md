---
title: "feat: Multi-source transaction import (AGF, MOV, NEG)"
type: feat
status: completed
date: 2026-03-29
---

# feat: Multi-source transaction import (AGF, MOV, NEG)

## Overview

Reimplement `bed transaction import` to support three mutually exclusive file sources via `--agf`, `--mov`, and `--neg` flags. Each source imports a specific subset of transaction data, reflecting the strengths of each B3/AGF export format:

- `--agf FILE`: Import everything (buy/sell, dividends, JSCP, rendimentos) from AGF+ app export
- `--mov FILE`: Import proventos (Dividendo, JSCP, Rendimento, Reembolso) + Tesouro/CDB/Opção trades + vencimentos from B3 Movimentação
- `--neg FILE`: Import stock buy/sell from B3 Negociação

## Problem Statement / Motivation

The current import only handles B3 "Movimentação" XLSX, which mixes actual trades with lending cycles (empréstimo automático), making it impossible to reliably identify real buy/sell operations for stocks. Analysis of the three available data sources revealed:

- **B3 Negociação** is the reliable source for stock buy/sell (clean Compra/Venda, no lending noise)
- **B3 Movimentação** is reliable for proventos (Dividendo, JSCP, Rendimento, Reembolso) and for Tesouro/CDB/Opção trades (which appear as explicit Compra/Venda)
- **AGF+** contains all operations correctly categorized, useful as an all-in-one import or for validation

Cross-validation showed 358/400 exact matches between AGF and Negociação, and 119/123 exact matches between AGF and Movimentação proventos.

## Proposed Solution

### CLI Interface

```bash
# Import from AGF+ (everything)
bed transaction import --agf agf.xlsx

# Import proventos + treasury/CDB/options from B3 Movimentação
bed transaction import --mov movimentacao.xlsx

# Import stock buy/sell from B3 Negociação
bed transaction import --neg negociacao.xlsx

# Dry-run (works with any source)
bed transaction import --neg negociacao.xlsx --dry-run
```

The three source flags are mutually exclusive. Each flag takes the file path as its value. The current positional `FILE` argument and `--sheet` option are removed.

### File Format Specifications

#### AGF+ (`--agf`)

- **File structure**: Row 1 empty, row 2 headers, data from row 3. 23 columns, only first 11 used.
- **Columns used**: Data Operação, Empresa, Num. Ações, Tipo, Origem, Valor, IRRF, Total Líquido, Fator, Data com, Status
- **Types to import**: Compra, Venda, Dividendo, Jscp, RENDIMENTO, Bonificação, Grupamento, Mudança Ticker, Desdobramento
- **Mapping**:

| AGF Column | Transaction Field | Notes |
|------------|-------------------|-------|
| Data Operação | `date` | DD/MM/YYYY |
| Tipo | `type` | Normalize: `Jscp` → `Juros Sobre Capital Próprio`, `RENDIMENTO` → `Rendimento` |
| Empresa | `product` | Full value (e.g., "ABEV3 - AMBEV") |
| Empresa (split) | `ticker` | Before " - " separator |
| (default) | `institution` | Default "inter", overridable with `--institution` |
| abs(Num. Ações) | `quantity` | Always stored as positive |
| Valor | `unit_value` | Unit price (not total) |
| abs(Total Líquido) | `total_value` | Negative for Venda |
| (discarded) | - | IRRF, Fator, Data com, Status, Origem: not stored |

- **Sign convention**: `total_value` negative for Venda, positive for Compra/proventos. `quantity` always positive.
- **IRRF**: Discarded (no model field). Can be enhanced later if needed.
- **Corporate actions** (Bonificação, Grupamento, Desdobramento, Mudança Ticker): Store as-is with whatever qty/values the file provides (often 0). Preserves the record for audit trail.

#### B3 Movimentação (`--mov`)

- **File structure**: Row 1 headers, data from row 2. 8 columns (existing parser).
- **Columns**: Entrada/Saída, Data, Movimentação, Produto, Instituição, Quantidade, Preço unitário, Valor da Operação
- **Type whitelist** (only these are imported):
  - `Dividendo`
  - `Juros Sobre Capital Próprio`
  - `Rendimento`
  - `Reembolso`
  - `Compra`
  - `Venda`
  - `COMPRA / VENDA`
  - `VENCIMENTO`
- **Excluded** (everything else, including):
  - `Transferência - Liquidação` (mixes lending with trades)
  - `Empréstimo`, `Transferência`, `Transferencia` (lending cycle)
  - `*-Transferido` variants (duplicates of regular proventos)
  - `Atualização`, `TRANSFERENCIA SEM FINANCEIRO`, `Cobrança de Taxa Semestral`
  - `Desdobro`, `Bonificação em Ativos`, `Leilão de Fração`, `Fração em Ativos`, `Grupamento`
- **Sign convention**: Existing `apply_sign()` based on Entrada/Saída (Credito=positive, Debito=negative)
- **Mapping**: Same as current implementation, just with type filtering applied

#### B3 Negociação (`--neg`)

- **File structure**: Row 1 headers, data from row 2. 9 columns.
- **Columns**: Data do Negócio, Tipo de Movimentação, Mercado, Prazo/Vencimento, Instituição, Código de Negociação, Quantidade, Preço, Valor
- **All market types imported**: Mercado à Vista, Mercado Fracionário, Opção de Compra/Venda sobre Ações
- **Mapping**:

| NEG Column | Transaction Field | Notes |
|------------|-------------------|-------|
| Data do Negócio | `date` | DD/MM/YYYY |
| Tipo de Movimentação | `type` | "Compra" or "Venda" |
| Código de Negociação | `ticker` | Strip "F" suffix for fracionário |
| Código de Negociação | `product` | Same as ticker (NEG has no company name) |
| Instituição | `institution` | Via existing `map_institution()` |
| Quantidade | `quantity` | Always positive |
| Preço | `unit_value` | Unit price |
| Valor | `total_value` | Positive for Compra, negative for Venda |
| Mercado | (not stored) | Not needed in model |
| Prazo/Vencimento | (not stored) | Not needed in model |

- **Fracionário ticker normalization**: Strip trailing "F" from tickers matching `[A-Z]{4}\d+F` pattern (e.g., `VALE3F` → `VALE3`)
- **Sign convention**: `total_value` positive for Compra, negative for Venda. `quantity` always positive.

### Type Normalization

All sources normalize to a canonical type vocabulary during import:

| Source | Raw Value | Canonical Value |
|--------|-----------|-----------------|
| AGF | `Jscp` | `Juros Sobre Capital Próprio` |
| AGF | `RENDIMENTO` | `Rendimento` |
| AGF | `Mudança Ticker` | `Mudança Ticker` |
| MOV | `Transferencia` | `Transferência` (existing) |
| MOV | `COMPRA / VENDA` | `COMPRA / VENDA` (kept as-is) |
| NEG | `Compra` | `Compra` |
| NEG | `Venda` | `Venda` |

### Cross-Source Deduplication

Row hashes are computed per-source using the same `compute_row_hash()` function. Since each source produces different field values for the same real-world event (different product names, institutions, dates), **cross-source dedup is not attempted**.

The recommended import pattern is:
- Use `--neg` for stock trades + `--mov` for proventos and treasury
- OR use `--agf` for everything (not both)

This should be documented in the `--help` text.

## Technical Considerations

### Architecture

The current `xlsx_import.py` is renamed/refactored into a module with source-specific parsers:

```
bed/services/
  xlsx_import.py          → keeps shared utilities (parse_date, parse_numeric, etc.)
  parsers/
    agf.py                → parse_agf_xlsx()
    mov.py                → parse_mov_xlsx() (extracted from current parse_xlsx)
    neg.py                → parse_neg_xlsx()
```

Alternative (simpler, preferred): Keep everything in `xlsx_import.py` with three parse functions. The file is small enough (~150 lines with all three parsers) that splitting into a module is premature.

**Decision: Keep single file `xlsx_import.py` with `parse_agf_xlsx()`, `parse_mov_xlsx()`, `parse_neg_xlsx()`.** Shared helpers (`parse_date`, `parse_numeric`, `extract_ticker`, `map_institution`, `apply_sign`) remain in the same file.

### Changes Summary

| File | Change |
|------|--------|
| `bed/services/xlsx_import.py` | Add `parse_agf_xlsx()`, `parse_neg_xlsx()`. Rename `parse_xlsx()` → `parse_mov_xlsx()`. Add MOV type whitelist. Add `normalize_agf_type()`. Add `strip_fracionario_suffix()`. |
| `bed/commands/transactions.py` | Replace `import_transactions()` CLI: remove positional FILE and `--sheet`, add mutually exclusive `--agf`/`--mov`/`--neg` options. Dispatch to correct parser. |
| `tests/test_xlsx_import.py` | Add tests for new parsers and helpers. |
| `tests/test_transactions_command.py` | Update import CLI tests for new flag syntax. |

### No Model Changes

The existing Transaction model accommodates all three sources without changes:
- `institution` (non-nullable): AGF defaults to "inter"
- `product` (String 500): NEG uses ticker as product
- All numeric fields handle the range of values across sources

## Acceptance Criteria

### Parser: `parse_agf_xlsx()`

- [ ] Correctly skips row 1 (empty) and row 2 (headers), reads data from row 3
- [ ] Extracts ticker from "Empresa" column using existing `extract_ticker()`
- [ ] Maps "Valor" → `unit_value`, "Total Líquido" → `total_value`
- [ ] Handles "-" values in IRRF, Valor, Num. Ações as 0
- [ ] Normalizes type: `Jscp` → `Juros Sobre Capital Próprio`, `RENDIMENTO` → `Rendimento`
- [ ] Handles negative qty in AGF (stores absolute value, sign only on total_value)
- [ ] Makes total_value negative for Venda
- [ ] Skips rows with no date (trailing empty rows)
- [ ] Skips the header row "Data Operação" if encountered as data
- [ ] Sets institution to default value ("inter")

### Parser: `parse_mov_xlsx()` (updated)

- [ ] Only imports rows matching the type whitelist
- [ ] Excludes all Transferência - Liquidação, Empréstimo, Transferência, *-Transferido, and other lending/corporate action types
- [ ] All existing parser behavior preserved (sign logic, ticker extraction, institution mapping)

### Parser: `parse_neg_xlsx()`

- [ ] Reads 9-column Negociação format
- [ ] Strips "F" suffix from fracionário tickers
- [ ] Uses ticker as product value
- [ ] Maps institution via existing `map_institution()`
- [ ] Applies sign: Compra = positive total, Venda = negative total
- [ ] Handles all market types (à Vista, Fracionário, Opções)
- [ ] Skips rows with no date

### CLI: `import` command

- [ ] `--agf`, `--mov`, `--neg` are mutually exclusive
- [ ] Exactly one source must be specified (error if none or multiple)
- [ ] `--dry-run` works with all three sources
- [ ] `--institution` option available (only meaningful for `--agf`, default "inter")
- [ ] Tag inference from assets DB works for all sources
- [ ] Dedup via row_hash works for all sources
- [ ] Help text documents recommended usage pattern

### Tests

- [ ] Unit tests for `parse_agf_xlsx()` helpers and type normalization
- [ ] Unit tests for `parse_neg_xlsx()` helpers and fracionário suffix stripping
- [ ] Unit tests for MOV type whitelist filtering
- [ ] Integration tests for CLI with each flag
- [ ] Integration test for mutually exclusive flag validation

## Implementation Phases

### Phase 1: Parsers

1. Add `MOV_TYPE_WHITELIST` constant and update `parse_xlsx()` → `parse_mov_xlsx()` with filtering
2. Add `parse_agf_xlsx()` with AGF-specific column mapping
3. Add `parse_neg_xlsx()` with NEG-specific column mapping
4. Add `normalize_agf_type()` and `strip_fracionario_suffix()` helpers
5. Write unit tests for all new functions

### Phase 2: CLI

1. Replace `import_transactions()` command:
   - Remove positional FILE argument and `--sheet` option
   - Add `--agf`, `--mov`, `--neg` as `click.option` with `type=click.Path(exists=True)`
   - Add `--institution` option (default "inter")
   - Add mutual exclusion validation
   - Dispatch to correct parser based on which flag is set
2. Write CLI integration tests

### Phase 3: Validation

1. Import AGF file and verify counts match expected (400 buy/sell + 190 proventos)
2. Import NEG file and verify stock trades match AGF (cross-reference)
3. Import MOV file and verify proventos match AGF (cross-reference)
4. Verify dry-run output for all three sources
5. Verify duplicate imports are properly skipped

## Sources & References

### Internal References

- Current parser: `bed/services/xlsx_import.py`
- Import command: `bed/commands/transactions.py:165-224`
- Transaction model: `bed/models/transaction.py`
- Bulk import service: `bed/services/transactions.py:70-88`
- Existing tests: `tests/test_xlsx_import.py`

### Data Analysis (this conversation)

- AGF vs Negociação: 358/400 exact matches on stock trades (ticker, qty, price, D+2)
- AGF vs Movimentação proventos: 119/123 exact matches (aggregated by date+ticker)
- Movimentação "-Transferido" entries: confirmed as duplicates of regular proventos, safe to exclude
- Movimentação "Transferência - Liquidação": confirmed as mix of lending + trades, must exclude for stocks
- Movimentação explicit "Compra"/"Venda": only for Tesouro, CDB, Opções (not stocks)
