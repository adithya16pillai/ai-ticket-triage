"""Auth routes: register, login, and current-user lookup."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.security import create_access_token
from app.auth.service import authenticate, create_user, get_user_by_email
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, TokenRead, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserRead:
    if get_user_by_email(db, payload.email) is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    return create_user(
        db,
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
    )


@router.post("/login", response_model=TokenRead)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenRead:
    user = authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(
        user.email, {"name": user.display_name, "role": user.role.value}
    )
    return TokenRead(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> UserRead:
    return user
