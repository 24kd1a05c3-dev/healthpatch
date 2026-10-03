import asyncio
import time
import math
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pymongo import ReturnDocument
from pymongo.errors import PyMongoError
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status

from app.config import settings


class InMemoryRateLimiter:
    def __init__(self):
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str, max_attempts: int, window_seconds: int) -> None:
        now = time.monotonic()
        async with self._lock:
            if key not in self._attempts and len(self._attempts) >= 4096:
                self._attempts = defaultdict(deque, {k: v for k, v in self._attempts.items()
                                                    if v and now - v[-1] <= window_seconds})
                if len(self._attempts) >= 8192:
                    raise HTTPException(429, 'Too many requests. Please try again later.')
            attempts = self._attempts[key]
            while attempts and now - attempts[0] > window_seconds:
                attempts.popleft()
            if len(attempts) >= max_attempts:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                )
            attempts.append(now)


rate_limiter = InMemoryRateLimiter()


async def check_limit(key: str, max_attempts: int, window_seconds: int):
    if settings.RATE_LIMIT_BACKEND == 'memory':
        return await rate_limiter.check(key, max_attempts, window_seconds)
    from app.database import get_collection
    now = datetime.now(timezone.utc)
    # Shared fixed windows; TTL is storage cleanup, never the enforcement clock.
    bucket = math.floor(now.timestamp() / window_seconds)
    identifier = sha256(f'{key}:{bucket}:{window_seconds}'.encode()).hexdigest()
    try:
        row = await get_collection('rate_limits').find_one_and_update(
            {'_id': identifier}, {'$inc': {'count': 1}, '$setOnInsert': {
                'expires_at': now + timedelta(seconds=window_seconds * 2)}},
            upsert=True, return_document=ReturnDocument.AFTER)
    except PyMongoError:
        raise HTTPException(503, 'Authentication temporarily unavailable') from None
    if row['count'] > max_attempts:
        retry = max(1, math.ceil((bucket + 1) * window_seconds - now.timestamp()))
        raise HTTPException(429, 'Too many requests. Please try again later.', headers={'Retry-After': str(retry)})


def rate_limit(key_builder: Callable[[Request], str], max_attempts: int | None = None, window_seconds: int | None = None):
    async def dependency(request: Request) -> None:
        await check_limit(
            key_builder(request),
            max_attempts or settings.RATE_LIMIT_AUTH_MAX_ATTEMPTS,
            window_seconds or settings.RATE_LIMIT_WINDOW_SECONDS,
        )

    return dependency


async def auth_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    await check_limit(
        f"auth:{client}:{request.url.path}",
        settings.RATE_LIMIT_AUTH_MAX_ATTEMPTS,
        settings.RATE_LIMIT_WINDOW_SECONDS,
    )
