"""
TABLZ — Redis-backed rate limiting middleware.
Login failures: 5 attempts → 15-min lockout.
General endpoints: configurable per-route limits.
"""

import redis.asyncio as redis

from app.config import settings

redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Get or create the Redis client."""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client


async def close_redis():
    """Close the Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


async def check_rate_limit(key: str, max_attempts: int, window_seconds: int) -> tuple[bool, int]:
    """
    Check if a rate limit has been exceeded.
    Returns (is_allowed, remaining_attempts).
    """
    r = await get_redis()
    current = await r.get(key)

    if current is None:
        await r.setex(key, window_seconds, 1)
        return True, max_attempts - 1

    count = int(current)
    if count >= max_attempts:
        ttl = await r.ttl(key)
        return False, 0

    await r.incr(key)
    return True, max_attempts - count - 1


async def increment_login_failure(admin_id: str) -> tuple[bool, int]:
    """
    Track failed login attempts. Returns (is_allowed, retry_after_seconds).
    5 failures → 15-min (900s) lockout.
    """
    key = f"ratelimit:login_fail:{admin_id}"
    is_allowed, remaining = await check_rate_limit(key, max_attempts=5, window_seconds=900)
    if not is_allowed:
        r = await get_redis()
        ttl = await r.ttl(key)
        return False, ttl
    return True, 0


async def reset_login_failures(admin_id: str):
    """Reset login failure counter on successful login."""
    r = await get_redis()
    await r.delete(f"ratelimit:login_fail:{admin_id}")


async def check_idempotency_key(key: str) -> str | None:
    """
    Check if an idempotency key has been used. Returns existing order_id or None.
    """
    r = await get_redis()
    return await r.get(f"idempotency:{key}")


async def set_idempotency_key(key: str, order_id: str):
    """Store an idempotency key → order_id mapping with 24h TTL."""
    r = await get_redis()
    await r.setex(f"idempotency:{key}", 86400, order_id)
