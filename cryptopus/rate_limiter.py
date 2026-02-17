import threading
import time
from typing import List


class RateLimiter:
    def __init__(self, max_calls: int = 10, period_seconds: float = 60.0) -> None:
        self._max_calls = max_calls
        self._period = period_seconds
        self._timestamps: List[float] = []
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        now = time.time()
        with self._lock:
            self._timestamps = [t for t in self._timestamps if now - t < self._period]
            if len(self._timestamps) >= self._max_calls:
                return False
            self._timestamps.append(now)
            return True
