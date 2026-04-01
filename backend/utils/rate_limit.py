"""In-memory rate limiter using a TTL sliding window."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class _Entry:
    timestamps: list[float] = field(default_factory=list)


class RateLimiter:
    """Simple in-memory rate limiter.

    Parameters
    ----------
    max_calls : int
        Maximum number of calls allowed within *window_seconds*.
    window_seconds : int
        Length of the sliding window in seconds.
    """

    def __init__(self, max_calls: int, window_seconds: int) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._entries: dict[str, _Entry] = {}
        self._lock = threading.Lock()

    def _prune(self, entry: _Entry, now: float) -> None:
        cutoff = now - self.window_seconds
        entry.timestamps = [t for t in entry.timestamps if t > cutoff]

    def is_allowed(self, key: str) -> bool:
        """Return True if the action is allowed (under the limit).

        Does **not** consume a slot — call :meth:`record` after the action
        succeeds to avoid counting failed attempts.
        """
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return True
            self._prune(entry, now)
            return len(entry.timestamps) < self.max_calls

    def record(self, key: str) -> None:
        """Record a successful action against *key*."""
        now = time.monotonic()
        with self._lock:
            entry = self._entries.setdefault(key, _Entry())
            self._prune(entry, now)
            entry.timestamps.append(now)

    def check_and_record(self, key: str) -> bool:
        """Convenience: check *and* record in one atomic step.

        Returns True if allowed (and records the call), False if rate-limited.
        """
        now = time.monotonic()
        with self._lock:
            entry = self._entries.setdefault(key, _Entry())
            self._prune(entry, now)
            if len(entry.timestamps) >= self.max_calls:
                return False
            entry.timestamps.append(now)
            return True

    def remaining(self, key: str) -> int:
        """Return how many calls remain for *key* in the current window."""
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return self.max_calls
            self._prune(entry, now)
            return max(0, self.max_calls - len(entry.timestamps))


# ── Pre-configured limiters for the application ──────────────────────

# Email sending: 3 per email address per hour
email_send_limiter = RateLimiter(max_calls=3, window_seconds=3600)

# Verification/reset code attempts: 5 per 15 minutes
code_attempt_limiter = RateLimiter(max_calls=5, window_seconds=900)

# Signup: 10 per IP per hour
signup_limiter = RateLimiter(max_calls=10, window_seconds=3600)

# Question generation: 10 per admin per hour
question_gen_limiter = RateLimiter(max_calls=10, window_seconds=3600)
