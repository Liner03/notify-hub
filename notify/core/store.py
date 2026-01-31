import time
from threading import Lock
from typing import Dict, Optional, Tuple


class MemoryStore:
    def __init__(self) -> None:
        self._expiry: Dict[str, float] = {}
        self._counters: Dict[str, Tuple[int, float]] = {}
        self._lock = Lock()
        self._last_sweep = 0.0
        self._sweep_interval = 60.0
        self._sweep_min_entries = 1024

    def _is_expired(self, expiry: float, now: Optional[float] = None) -> bool:
        return expiry <= (now if now is not None else time.time())

    def _maybe_sweep(self, now: float) -> None:
        if now - self._last_sweep < self._sweep_interval:
            return
        if len(self._expiry) + len(self._counters) < self._sweep_min_entries:
            return
        self._last_sweep = now
        for key, expiry in list(self._expiry.items()):
            if self._is_expired(expiry, now):
                self._expiry.pop(key, None)
        for key, (_, expiry) in list(self._counters.items()):
            if expiry and self._is_expired(expiry, now):
                self._counters.pop(key, None)

    def is_active(self, key: str) -> bool:
        with self._lock:
            now = time.time()
            self._maybe_sweep(now)
            expiry = self._expiry.get(key)
            if expiry is None:
                return False
            if self._is_expired(expiry, now):
                self._expiry.pop(key, None)
                return False
            return True

    def set_expiry(self, key: str, ttl: int) -> None:
        with self._lock:
            now = time.time()
            self._maybe_sweep(now)
            self._expiry[key] = now + ttl

    def increment(self, key: str, ttl: int) -> int:
        with self._lock:
            now = time.time()
            self._maybe_sweep(now)
            count, expiry = self._counters.get(key, (0, 0))
            if expiry and self._is_expired(expiry, now):
                count = 0
            count += 1
            self._counters[key] = (count, now + ttl)
            return count

    def get_count(self, key: str) -> int:
        with self._lock:
            now = time.time()
            self._maybe_sweep(now)
            count, expiry = self._counters.get(key, (0, 0))
            if expiry and self._is_expired(expiry, now):
                self._counters.pop(key, None)
                return 0
            return count

    def reset(self, key: str) -> None:
        with self._lock:
            self._counters.pop(key, None)
            self._expiry.pop(key, None)
