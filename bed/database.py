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
        await _add_column_if_missing(conn, "rules", "proportion", "NUMERIC(5, 2)")


async def _add_column_if_missing(conn, table, column, col_type):
    result = await conn.exec_driver_sql(f"PRAGMA table_info({table})")
    columns = [row[1] for row in result]
    if column not in columns:
        await conn.exec_driver_sql(
            f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
        )
