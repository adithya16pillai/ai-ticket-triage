"""RQ worker job for async triage.

Run the worker with:  rq worker -u $REDIS_URL triage

The job calls the *unchanged* triage service from a background process — the
isolation of the triage boundary is what lets the caller move from request
thread to worker thread for free, with all the never-raises/validation/fallback
guarantees intact.
"""
import logging
import uuid

from app import crud
from app.database import SessionLocal

logger = logging.getLogger("worker")


def run_triage_job(ticket_id: str) -> None:
    db = SessionLocal()
    try:
        ticket = crud.get_ticket(db, uuid.UUID(ticket_id))
        if ticket is None:
            logger.warning("triage job: ticket %s not found", ticket_id)
            return
        crud.apply_triage_job(db, ticket)
    finally:
        db.close()
