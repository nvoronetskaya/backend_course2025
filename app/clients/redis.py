import redis.asyncio as redis
from typing import Optional
from contextlib import asynccontextmanager
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

@asynccontextmanager
async def get_redis_connection():
    connection = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    try:
        yield connection
    finally:
        await connection.aclose()
