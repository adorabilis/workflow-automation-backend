import json
from datetime import datetime
from enum import Enum
from functools import lru_cache
from typing import Any, Iterable, cast

import redis

from core.config import REDIS_DB, REDIS_HOST, REDIS_PORT

# Create a global Redis connection pool
redis_pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    max_connections=20,
    decode_responses=True,
)


@lru_cache()
def get_redis_cache() -> "RedisCache":
    """Factory function that returns a singleton RedisCache instance."""
    return RedisCache()


class RedisCache:
    """Redis-based caching implementation with connection pooling."""

    def __init__(self):
        self.redis = redis.Redis(connection_pool=redis_pool)

    def get(self, key: str) -> dict[str, Any] | None:
        """Get a value from the cache."""
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set a value in the cache with optional expiry in seconds."""
        value = _serialize_model(value)
        self.redis.set(key, json.dumps(value), ex=ttl)

    def delete(self, key: str) -> None:
        """Delete a key from the cache."""
        self.redis.delete(key)

    def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching a pattern."""
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)


def _serialize_model(obj: Any) -> Any:
    """
    Generic serializer for SQLModel objects that dynamically handles attributes.
    """
    # Handle None
    if obj is None:
        return None

    # Handle datetime objects
    if isinstance(obj, datetime):
        return obj.isoformat()

    # Handle Enum objects
    if isinstance(obj, Enum):
        return obj.value

    # Handle lists (like the tasks relationship)
    if isinstance(obj, list):
        return [_serialize_model(item) for item in cast(Iterable[Any], obj)]

    # Handle dictionaries (like JSON fields)
    if isinstance(obj, dict):
        return {k: _serialize_model(v) for k, v in cast(Iterable[Any], obj.items())}

    # Handle SQLModel objects
    if (
        hasattr(obj, "__dict__")
        and hasattr(obj, "__class__")
        and hasattr(obj.__class__, "__tablename__")
    ):
        result = {}

        # Get all model attributes (this works for SQLModel objects)
        for key, value in obj.__dict__.items():
            # Skip private attributes and relationship back-references to avoid cycles
            if not key.startswith("_") and key != "workflow":
                result[key] = _serialize_model(value)

        return result

    # Return primitive types as is
    return obj
