from __future__ import annotations

import time
from collections.abc import Hashable
from dataclasses import dataclass
from threading import RLock
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class CacheEntry(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int = 300, max_size: int = 512) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._items: dict[Hashable, CacheEntry[T]] = {}
        self._lock = RLock()

    def get(self, key: Hashable) -> T | None:
        now = time.time()
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            if item.expires_at <= now:
                self._items.pop(key, None)
                return None
            return item.value

    def set(self, key: Hashable, value: T) -> None:
        with self._lock:
            if len(self._items) >= self.max_size:
                oldest = min(self._items, key=lambda item_key: self._items[item_key].expires_at)
                self._items.pop(oldest, None)
            self._items[key] = CacheEntry(value=value, expires_at=time.time() + self.ttl_seconds)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
