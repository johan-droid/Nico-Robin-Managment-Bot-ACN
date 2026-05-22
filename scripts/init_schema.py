from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.database import DatabaseManager


async def run() -> None:
    db_path = os.getenv("BOT_DB_PATH", "data/nico_robin.db")
    db = await DatabaseManager.get_instance(db_path=db_path)
    await db.initialize()
    await db.close()
    print(f"Schema initialized at {db_path}")


if __name__ == "__main__":
    asyncio.run(run())
