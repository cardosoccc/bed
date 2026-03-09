"""Standalone migration script. Run via: uv run python -m bed.migrate"""

import asyncio

from bed.database import migrate


def main():
    asyncio.run(migrate())
    print("migration complete.")


if __name__ == "__main__":
    main()
