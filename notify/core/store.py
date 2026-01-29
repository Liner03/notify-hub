import time
from threading import Lock
from typing import Dict, Tuple


class MemoryStore:
    def __init__(self) -> None:
        self._expiry: Dict[str, float] = {}
        self._counters: Dict[str, Tuple[int, float]] = {}
        self._lock = Lock()

    def _is_expired(self, expiry: float) -> bool:
        return expiry <= time.time()

    def is_active(self, key: str) -> bool:
        with self._lock:
            expiry = self._expiry.get(key)
            if expiry is None:
                return False
            if self._is_expired(expiry):
                self._expiry.pop(key, None)
                return False
            return True

    def set_expiry(self, key: str, ttl: int) -> None:
        with self._lock:
            self._expiry[key] = time.time() + ttl

    def increment(self, key: str, ttl: int) -> int:
        with self._lock:
            count, expiry = self._counters.get(key, (0, 0))
            if expiry and self._is_expired(expiry):
                count = 0
            count += 1
            self._counters[key] = (count, time.time() + ttl)
            return count

    def get_count(self, key: str) -> int:
        with self._lock:
            count, expiry = self._counters.get(key, (0, 0))
            if expiry and self._is_expired(expiry):
                self._counters.pop(key, None)
                return 0
            return count

    def reset(self, key: str) -> None:
        with self._lock:
            self._counters.pop(key, None)
            self._expiry.pop(key, None)
