from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginIn, MeUpdateIn, RegisterIn, TokenOut, UserOut

router = APIRouter()


def _user_out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, display_name=u.display_name or "User")


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    uid = getattr(request.state, "user_id", None)
    if uid is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    u = db.get(User, int(uid))
    if not u:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return u


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    email = body.email.lower().strip()
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    name = (body.display_name or "").strip() or email.split("@")[0]
    u = User(
        email=email,
        hashed_password=hash_password(body.password),
        display_name=name[:255],
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    token = create_access_token(u.id)
    return TokenOut(access_token=token, user=_user_out(u))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    email = body.email.lower().strip()
    u = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not u or not verify_password(body.password, u.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token(u.id)
    return TokenOut(access_token=token, user=_user_out(u))


@router.get("/me", response_model=UserOut)
def get_me(u: User = Depends(get_current_user)) -> UserOut:
    return _user_out(u)


@router.patch("/me", response_model=UserOut)
def patch_me(body: MeUpdateIn, u: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserOut:
    if body.display_name is not None and body.display_name.strip():
        u.display_name = body.display_name.strip()[:255]
    db.add(u)
    db.commit()
    db.refresh(u)
    return _user_out(u)
