from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.session import get_session_factory


async def new_session() -> AsyncSession:
    return get_session_factory()()
