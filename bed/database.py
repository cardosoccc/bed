from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_PATH = Path.home() / ".bed" / "bed.db"
DB_URL = f"sqlite+aiosqlite:///{DB_PATH}"


def _make_engine(url: str = DB_URL):
    engine = create_async_engine(url, echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


engine = _make_engine()
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables():
    Path.home().joinpath(".bed").mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def migrate():
    """Add columns that may be missing from older databases."""
    async with engine.begin() as conn:
        await _add_column_if_missing(conn, "rules", "current", "BOOLEAN NOT NULL DEFAULT 1")
        await _add_column_if_missing(conn, "rules", "target", "NUMERIC(18, 2)")
        await _add_column_if_missing(conn, "rules", "min", "NUMERIC(18, 2)")
        await _add_column_if_missing(conn, "rules", "max", "NUMERIC(18, 2)")
        await _copy_legacy_rule_values(conn)
        await _rename_table_if_exists(conn, "tickers", "stocks")


async def _rename_table_if_exists(conn, old_name, new_name):
    result = await conn.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=:old",
        {"old": old_name},
    )
    if result.first():
        await conn.exec_driver_sql(f"ALTER TABLE {old_name} RENAME TO {new_name}")


async def _add_column_if_missing(conn, table, column, col_type):
    result = await conn.exec_driver_sql(f"PRAGMA table_info({table})")
    columns = [row[1] for row in result]
    if column not in columns:
        await conn.exec_driver_sql(
            f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
        )


async def _copy_legacy_rule_values(conn):
    columns = await _get_columns(conn, "rules")
    if "target" not in columns or "current" not in columns:
        return

    if "proportion" in columns:
        await conn.exec_driver_sql(
            """
            UPDATE rules
            SET target = proportion, current = 1
            WHERE target IS NULL AND proportion IS NOT NULL
            """
        )

    if "current_value" in columns:
        await conn.exec_driver_sql(
            """
            UPDATE rules
            SET target = current_value, current = 1
            WHERE target IS NULL AND current_value IS NOT NULL
            """
        )

    if "invested_value" in columns:
        await conn.exec_driver_sql(
            """
            UPDATE rules
            SET target = invested_value, current = 0
            WHERE target IS NULL AND invested_value IS NOT NULL
            """
        )


async def _get_columns(conn, table):
    result = await conn.exec_driver_sql(f"PRAGMA table_info({table})")
    return [row[1] for row in result]
