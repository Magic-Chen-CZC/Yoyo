from arq import ArqRedis, create_pool
from arq.connections import RedisSettings

from yoyo.core.config import get_settings


async def get_job_pool() -> ArqRedis:
    settings = get_settings()
    return await create_pool(RedisSettings.from_dsn(settings.redis_url))
