"""Redis/RQ enqueue helper for async triage.

redis + rq are imported lazily so the app (and tests, and the sync-mode demo)
run without them installed. Enqueuing never raises: if Redis is unreachable the
ticket simply stays in its valid `fallback` state and the manual queue works —
the same failure mode as a synchronous triage that fell back.
"""
import logging

from app.config import settings

logger = logging.getLogger("queue")

TRIAGE_QUEUE = "triage"


def _get_queue():
    from redis import Redis
    from rq import Queue

    return Queue(TRIAGE_QUEUE, connection=Redis.from_url(settings.redis_url))


def enqueue_triage(ticket_id) -> bool:
    """Enqueue a triage job. Returns True if enqueued, False on any failure
    (which is safe — the ticket remains a valid fallback)."""
    try:
        _get_queue().enqueue("app.worker.run_triage_job", str(ticket_id))
        return True
    except Exception as exc:  # redis down / rq missing — never block creation
        logger.warning("failed to enqueue triage for %s: %s", ticket_id, exc)
        return False
