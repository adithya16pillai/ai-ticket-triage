"""A process-monotonic UTC clock.

The audit timeline and comment thread order by created_at. The OS wall clock
(especially on Windows, ~15ms resolution) can hand back identical timestamps for
events written microseconds apart, which would make ordering fall back to a
random tiebreaker. This guarantees each call returns a value strictly greater
than the previous, so insertion order is preserved without a sequence column.
"""
import threading
from datetime import datetime, timedelta, timezone

_lock = threading.Lock()
_last: datetime | None = None


def monotonic_now() -> datetime:
    global _last
    with _lock:
        now = datetime.now(timezone.utc)
        if _last is not None and now <= _last:
            now = _last + timedelta(microseconds=1)
        _last = now
        return now
