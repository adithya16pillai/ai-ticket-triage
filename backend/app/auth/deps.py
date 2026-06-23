"""FastAPI auth dependencies.

`get_current_user` strictly requires a valid bearer token (used by /auth/me and
any protected route). `current_actor` is the soft variant the ticket routes use:
it returns the agent's name for the audit log, or None when auth is disabled so
the single-agent demo still runs without tokens.
"""
import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.auth.service import get_user_by_email
from app.config import settings
from app.database import get_db
from app.models import User


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return authorization.split(" ", 1)[1]


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    token = _bearer_token(authorization)
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    email = payload.get("sub")
    user = get_user_by_email(db, email) if email else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


def current_actor(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> str | None:
    """The display name to stamp on audit events, or None in open/demo mode."""
    if not settings.auth_enabled:
        return None
    return get_current_user(authorization=authorization, db=db).display_name
