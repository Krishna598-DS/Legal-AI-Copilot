"""Rate limiting backed by Redis when available, else DB/memory."""

from __future__ import annotations

import time
from threading import Lock

from src.config import get_settings
from src.logging_config import logger

settings = get_settings()

_memory: dict[str, list[float]] = {}
_lock = Lock()
_redis = None


def _get_redis():
    global _redis
    if _redis is not None:
        return _redis
    if not settings.REDIS_URL:
        return None
    try:
        import redis

        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        _redis = client
        logger.info("Redis connected for rate limiting")
        return _redis
    except Exception as exc:
        logger.warning("Redis unavailable, using memory rate limits: %s", exc)
        _redis = False  # type: ignore
        return None


def hit(key: str, limit: int, window_seconds: int = 3600) -> tuple[bool, int]:
    """
    Record a hit. Returns (allowed, current_count).
    allowed=False means limit exceeded (hit not counted when using redis INCR after check —
    we count then reject if over).
    """
    client = _get_redis()
    now = time.time()

    if client:
        rkey = f"rl:{key}"
        pipe = client.pipeline()
        pipe.incr(rkey)
        pipe.expire(rkey, window_seconds)
        count, _ = pipe.execute()
        count = int(count)
        return count <= limit, count

    with _lock:
        stamps = _memory.get(key, [])
        cutoff = now - window_seconds
        stamps = [t for t in stamps if t >= cutoff]
        if len(stamps) >= limit:
            _memory[key] = stamps
            return False, len(stamps)
        stamps.append(now)
        _memory[key] = stamps
        return True, len(stamps)


def current_count(key: str, window_seconds: int = 3600) -> int:
    client = _get_redis()
    if client:
        val = client.get(f"rl:{key}")
        return int(val or 0)

    now = time.time()
    with _lock:
        stamps = _memory.get(key, [])
        cutoff = now - window_seconds
        stamps = [t for t in stamps if t >= cutoff]
        _memory[key] = stamps
        return len(stamps)
