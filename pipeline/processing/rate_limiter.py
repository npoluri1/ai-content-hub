import time
import threading
from collections import deque


class RateLimiter:
    def __init__(self, domain: str, requests_per_minute: int = 10, burst: int = 3):
        self.domain = domain
        self.requests_per_minute = requests_per_minute
        self.burst = burst
        self._lock = threading.Lock()
        self._timestamps = deque()
        self._last_request = 0.0

    def wait_if_needed(self) -> float:
        waited = 0.0
        with self._lock:
            now = time.monotonic()
            cutoff = now - 60.0
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()

            recent_count = len(self._timestamps)
            burst_window = now - 1.0
            burst_count = sum(1 for t in self._timestamps if t > burst_window)

            if recent_count >= self.requests_per_minute:
                sleep_time = self._timestamps[0] + 60.0 - now
                if sleep_time > 0:
                    self._lock.release()
                    time.sleep(sleep_time)
                    self._lock.acquire()
                    waited += sleep_time
                    now = time.monotonic()
                    cutoff = now - 60.0
                    while self._timestamps and self._timestamps[0] < cutoff:
                        self._timestamps.popleft()
                    burst_count = sum(1 for t in self._timestamps if t > now - 1.0)

            if burst_count >= self.burst:
                sleep_time = 1.0
                time.sleep(sleep_time)
                waited += sleep_time
                now = time.monotonic()

            self._timestamps.append(time.monotonic())
            self._last_request = time.monotonic()

        return waited

    def can_request(self) -> bool:
        with self._lock:
            now = time.monotonic()
            cutoff = now - 60.0
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()

            if len(self._timestamps) >= self.requests_per_minute:
                return False
            burst_count = sum(1 for t in self._timestamps if t > now - 1.0)
            if burst_count >= self.burst:
                return False
            return True

    def record_request(self):
        with self._lock:
            self._timestamps.append(time.monotonic())
            self._last_request = time.monotonic()

    def get_stats(self) -> dict:
        with self._lock:
            now = time.monotonic()
            cutoff = now - 60.0
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()

            requests_made = len(self._timestamps)
            requests_remaining = max(0, self.requests_per_minute - requests_made)
            avg_delay = 0.0
            if requests_made > 1:
                timestamps_list = list(self._timestamps)
                delays = [timestamps_list[i + 1] - timestamps_list[i] for i in range(len(timestamps_list) - 1)]
                avg_delay = sum(delays) / len(delays) if delays else 0.0

            return {
                "domain": self.domain,
                "requests_made": requests_made,
                "requests_remaining": requests_remaining,
                "last_request": self._last_request,
                "avg_delay": avg_delay,
            }


class GlobalRateLimiter:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._limiters = {}
                    cls._instance._global_lock = threading.Lock()
        return cls._instance

    def get_limiter(self, domain: str) -> RateLimiter:
        with self._global_lock:
            if domain not in self._limiters:
                self._limiters[domain] = RateLimiter(domain)
            return self._limiters[domain]

    def wait(self, domain: str):
        limiter = self.get_limiter(domain)
        limiter.wait_if_needed()
