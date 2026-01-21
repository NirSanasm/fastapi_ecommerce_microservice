"""Product Service Database Configuration"""

import sys
from pathlib import Path
from typing import AsyncGenerator

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from shared.database import DatabaseManager, Base
from app.config import settings


db_manager = DatabaseManager(database_url=settings.database_url, echo=settings.debug)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with db_manager.async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
