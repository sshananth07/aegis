import hashlib
import structlog
import time
from typing import Optional, Any

logger = structlog.get_logger()

# In-memory cache as fallback (no Redis needed for MVP)
# Keys are scoped per-user to prevent cross-user cache leakage
_cache: dict = {}


def _make_key(prefix: str, *args, **kwargs) -> str:
    raw = f"{prefix}:{args}:{sorted(kwargs.items())}"
    return hashlib.md5(raw.encode()).hexdigest()


def make_user_key(user_id: str, key: str) -> str:
    """Scope a cache key to a specific user to prevent cache leakage."""
    return f"user:{user_id}:{key}"


def cache_get(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if entry is None:
        return None
    value, expires_at = entry
    if time.time() > expires_at:
        del _cache[key]
        return None
    return value


def cache_set(key: str, value: Any, ttl_seconds: int = 300):
    _cache[key] = (value, time.time() + ttl_seconds)
    logger.info("cache_set", key=key, ttl=ttl_seconds)


def cache_delete(key: str):
    _cache.pop(key, None)


def cache_clear_prefix(prefix: str):
    keys_to_delete = [k for k in _cache if k.startswith(prefix)]
    for k in keys_to_delete:
        del _cache[k]


def cache_clear_user(user_id: str):
    """Clear all cache entries for a specific user."""
    prefix = f"user:{user_id}:"
    cache_clear_prefix(prefix) 