import json
import hashlib
import structlog
from typing import Optional, Any
from functools import wraps

logger = structlog.get_logger()

# In-memory cache as fallback (no Redis needed for MVP)
_cache: dict = {}

def _make_key(prefix: str, *args, **kwargs) -> str:
    raw = f"{prefix}:{args}:{sorted(kwargs.items())}"
    return hashlib.md5(raw.encode()).hexdigest()

def cache_get(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if entry is None:
        return None
    value, ttl_remaining = entry
    return value

def cache_set(key: str, value: Any, ttl_seconds: int = 300):
    _cache[key] = (value, ttl_seconds)
    logger.info("cache_set", key=key, ttl=ttl_seconds)

def cache_delete(key: str):
    _cache.pop(key, None)

def cache_clear_prefix(prefix: str):
    keys_to_delete = [k for k in _cache if k.startswith(prefix)]
    for k in keys_to_delete:
        del _cache[k]