# bed - portfolio management cli

A local-first portfolio management CLI tool for tracking and managing personal financial assets. Built to be used by both humans and AI agents. The name comes from "keeping your money under the bed."

Follows the same design principles as [bud](https://github.com/cardosoccc/bud) (budget management CLI).

## project goals

- provide a fast, local-first CLI for managing investment portfolios
- track assets with rich metadata (class, type, category, tags)
- define rules to set target allocations and value limits
- generate portfolio status reports with breakdowns by class and tags
- support cloud synchronization via AWS S3 and Google Cloud Storage
- offer a concise command interface with single-letter aliases for speed
- be AI-agent friendly with structured, predictable output

## concepts

- **portfolio** — the top-level project. there is no separate portfolio table; the database itself represents the portfolio. a portfolio is initialized, destroyed, pushed, or pulled as a unit.
- **asset** — a specific holding in the portfolio (e.g. a stock, bond, ETF, crypto position). each asset tracks quantity, initial investment value, and current market value. assets can be organized with categories, subcategories, and tags.
- **rule** — a constraint or target for portfolio allocation. rules define a `target`, `min`, or `max` threshold against either current or invested portfolio value. values between `0` and `1` are interpreted as proportions of the portfolio total for the chosen metric. rules can be scoped to a specific asset class, asset type, category, subcategory, or set of tags.
- **cloud sync** — portfolios can be pushed to and pulled from remote cloud storage (S3 or GCS) with version tracking to prevent accidental overwrites.

## domain model

### asset

| attribute       | type                                                    | description                       |
|-----------------|---------------------------------------------------------|-----------------------------------|
| id              | UUID                                                    | unique identifier (auto-generated)|
| name            | string                                                  | asset name (e.g. "AAPL")         |
| description     | string (optional)                                       | free-text description             |
| asset_class     | enum: `equity`, `fixed-income`                          | broad asset classification        |
| asset_type      | enum: `stock`, `bond`, `fund`, `etf`, `reit`, `crypto`, `other` | specific asset type      |
| quantity        | numeric (18,8)                                          | number of units held              |
| initial_value   | numeric (18,2)                                          | total amount invested             |
| current_value   | numeric (18,2)                                          | current market value              |
| category        | string (optional)                                       | organizational category           |
| subcategory     | string (optional)                                       | organizational subcategory        |
| tags            | list of strings                                         | flexible labels for grouping      |
| created_at      | datetime                                                | creation timestamp                |

### rule

| attribute       | type              | description                                     |
|-----------------|-------------------|-------------------------------------------------|
| id              | UUID              | unique identifier (auto-generated)              |
| description     | string            | rule description                                |
| current         | boolean           | `true` for current-value rules, `false` for invested-value rules |
| target          | numeric (18,2)    | exact target for the selected metric (optional) |
| min             | numeric (18,2)    | lower bound for the selected metric (optional)  |
| max             | numeric (18,2)    | upper bound for the selected metric (optional)  |
| asset_class     | string (optional) | filter by asset class                           |
| asset_type      | string (optional) | filter by asset type                            |
| category        | string (optional) | filter by category                              |
| subcategory     | string (optional) | filter by subcategory                           |
| tags            | list of strings   | filter by tags                                  |
| created_at      | datetime          | creation timestamp                              |

## commands

### portfolio

| command                        | description                              |
|--------------------------------|------------------------------------------|
| `bed portfolio init`           | initialize a new portfolio database      |
| `bed portfolio destroy`        | delete the portfolio database (confirms) |
| `bed portfolio push [--force]` | push database to cloud storage           |
| `bed portfolio pull [--force]` | pull database from cloud storage         |
| `bed portfolio status`         | show portfolio report (classes and tags)  |

### asset

| command                              | description                   |
|--------------------------------------|-------------------------------|
| `bed asset list`                     | list all assets in a table    |
| `bed asset create [options]`         | add a new asset               |
| `bed asset edit <identifier> [options]` | update an existing asset   |
| `bed asset delete <identifier>`      | remove an asset (confirms)    |

**asset create options:**

```
--name, -n         asset name (required)
--description, -d  asset description
--class            asset class: equity, fixed-income (required)
--type             asset type: stock, bond, fund, etf, reit, crypto, other (required)
--quantity, -q     quantity (default: 0)
--initial-value, -i  initial value (default: 0)
--current-value, -c  current value (default: 0)
--category         category
--subcategory      subcategory
--tags, -t         comma-separated tags
```

**asset edit** accepts the same options; only provided fields are updated. the `<identifier>` can be a UUID, a numeric index from the list, or the asset name.

### rule

| command                              | description                |
|--------------------------------------|----------------------------|
| `bed rule list`                      | list all rules             |
| `bed rule create [options]`          | add a new rule             |
| `bed rule edit <identifier> [options]` | update an existing rule  |
| `bed rule delete <identifier>`       | remove a rule (confirms)   |

### config

| command                        | description                        |
|--------------------------------|------------------------------------|
| `bed config set <key> <value>` | set a configuration value          |
| `bed config list`              | show all configuration values      |
| `bed config aws`               | configure AWS credentials (prompted) |
| `bed config gcp`               | configure GCP credentials (prompted) |

## aliases

Single-letter aliases are available for fast usage.

### command group aliases

| alias | expands to  |
|-------|-------------|
| `a`   | `asset`     |
| `r`   | `rule`      |
| `p`   | `portfolio` |
| `c`   | `config`    |

### subcommand aliases

| alias | expands to |
|-------|------------|
| `l`   | `list`     |
| `c`   | `create`   |
| `e`   | `edit`     |
| `d`   | `delete`   |
| `s`   | `status` (portfolio) / `set` (config) |

### double-letter shortcuts

| shortcut | equivalent          |
|----------|---------------------|
| `aa`     | `asset list`        |
| `rr`     | `rule list`         |
| `pp`     | `portfolio status`  |

### examples

```bash
bed a l                  # list assets
bed a c -n AAPL --class equity --type stock -q 10 -i 1500 -c 1700
bed a e AAPL -c 1800     # update current value
bed a d AAPL             # delete asset

bed r l                  # list rules
bed r c --description "equity target" --class equity --target 0.60
bed r c --description "bond floor" --class fixed-income --min 0.20
bed r c --description "invested equity cap" --class equity --target 5000 --invested

bed p s                  # portfolio status
bed pp                   # same as above

bed c s bucket s3://my-bucket/portfolios
bed p push               # sync to cloud
```

## architecture

```
bed/
├── cli.py                     # main CLI entry point, alias management
├── commands/
│   ├── assets.py              # asset CRUD commands (click)
│   ├── rules.py               # rule CRUD commands (click)
│   ├── db_commands.py         # portfolio commands (init, destroy, push, pull, status)
│   ├── credentials.py         # AWS/GCP credential configuration prompts
│   ├── config_store.py        # user configuration storage (~/.bed/config.json)
│   ├── db.py                  # database session management, async runner
│   └── utils.py               # helpers (resolve asset/rule by ID, index, or name)
├── services/
│   ├── assets.py              # asset CRUD operations (async)
│   ├── rules.py               # rule CRUD operations (async)
│   ├── portfolio.py           # portfolio analysis and status reporting
│   └── storage.py             # cloud storage providers (S3, GCS)
├── models/
│   ├── asset.py               # Asset SQLAlchemy model + enums
│   └── rule.py                # Rule SQLAlchemy model
├── schemas/
│   ├── asset.py               # Pydantic schemas (AssetCreate, AssetRead, AssetUpdate)
│   └── rule.py                # Pydantic schemas (RuleCreate, RuleRead, RuleUpdate)
├── database.py                # SQLAlchemy async engine, session factory, Base
├── config.py                  # settings management
├── credentials.py             # credential storage (AWS keys, GCP path)
└── migrate.py                 # database migration script
```

### layered design

```
CLI (click commands)  →  Services (business logic)  →  Models (SQLAlchemy ORM)  →  SQLite
```

- **CLI layer** — click groups and commands handle argument parsing, user interaction, and output formatting
- **Service layer** — async functions that perform CRUD operations and portfolio analysis
- **Model layer** — SQLAlchemy ORM models with mapped columns and enums
- **Schema layer** — Pydantic models for input validation and serialization (Create, Read, Update)
- **Storage layer** — strategy pattern with S3Provider and GCSProvider for cloud sync

### key design decisions

- **async-first** — all database operations use SQLAlchemy asyncio with aiosqlite
- **local-first** — SQLite database stored at `~/.bed/bed.db`; cloud sync is optional
- **flexible ID resolution** — assets and rules can be referenced by UUID, numeric index (from list output), or name
- **version-tracked sync** — push/pull uses a `sync_meta.json` file to prevent accidental overwrites; `--force` overrides
- **backup on pull** — pulling from cloud creates a `.db.bak` backup of the local database

### file storage

| path                        | purpose                        |
|-----------------------------|--------------------------------|
| `~/.bed/bed.db`             | SQLite portfolio database      |
| `~/.bed/config.json`        | user configuration             |
| `~/.bed/credentials.json`   | cloud provider credentials (mode 0600) |
| `~/.bed/sync_meta.json`     | version tracking for push/pull |

## dependencies

### runtime

| package                  | version  | purpose                       |
|--------------------------|----------|-------------------------------|
| click                    | >= 8.1   | CLI framework                 |
| sqlalchemy               | >= 2.0   | async ORM                     |
| aiosqlite                | >= 0.20  | async SQLite driver           |
| pydantic                 | >= 2.0   | data validation               |
| pydantic-settings        | >= 2.0   | settings management           |
| tabulate                 | >= 0.9   | table-formatted output        |
| boto3                    | >= 1.34  | AWS S3 cloud storage          |
| google-cloud-storage     | >= 2.14  | Google Cloud Storage          |

### development

| package                  | version  | purpose                       |
|--------------------------|----------|-------------------------------|
| pytest                   | >= 8.0   | testing framework             |
| pytest-asyncio           | >= 0.23  | async test support            |

### build

- **build backend:** hatchling
- **package manager:** uv
- **python:** >= 3.13

## setup

```bash
# create virtual environment and install dependencies
make setup

# or manually
uv venv
uv sync
```

## usage

```bash
# initialize a portfolio
bed portfolio init

# add assets
bed asset create -n AAPL --class equity --type stock -q 10 -i 1500 -c 1700
bed asset create -n VGLT --class fixed-income --type etf -q 50 -i 3000 -c 3200 -t bonds,long-term

# add rules
bed rule create --description "equity allocation" --class equity --target 0.60
bed rule create --description "fixed-income allocation" --class fixed-income --target 0.40

# view portfolio status
bed portfolio status

# configure cloud sync
bed config set bucket s3://my-bucket/portfolios
bed config aws

# push to cloud
bed portfolio push
```

## testing

```bash
# run all tests
make test

# or manually
uv run pytest tests/ -v
```

tests use an in-memory SQLite database and `click.testing.CliRunner` for integration tests. test markers:

- `@pytest.mark.asyncio` — async unit tests
- `@pytest.mark.integration` — CLI runner integration tests

## development

```bash
make setup     # create venv and install dependencies
make test      # run tests
make lint      # check code with ruff
make migrate   # run database migrations
make clean     # remove build artifacts and caches
```

## references

- [bud](https://github.com/cardosoccc/bud) — budget management CLI (design reference)
