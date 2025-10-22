from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.user import User
from app.schemas.user import UserCreateIn, UserOut, MeUpdateIn
from app.core.security import hash_password, get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreateIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="EMAIL_DUPLICATE")
    if db.query(User).filter(User.nickname == payload.nickname).first():
        raise HTTPException(status_code=400, detail="NICKNAME_DUPLICATE")

    user = User(
        email=payload.email,
        nickname=payload.nickname,
        birth_date=payload.birth_date,
        password_hash=hash_password(payload.password),
        introduction="",
        image_url=None,
        category="",
        sell_count=0,
        buy_count=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.get("/me", response_model=UserOut)
def get_me(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    me = db.query(User).filter(User.user_id == current.user_id).first()
    if not me:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")
    return me

@router.patch("/me", response_model=UserOut)
def update_me(payload: MeUpdateIn, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    me = db.query(User).filter(User.user_id == current.user_id).first()
    if not me:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")

    data = payload.model_dump(exclude_unset=True, by_alias=False)

    if "nickname" in data:
        exists = db.query(User).filter(User.nickname == data["nickname"], User.user_id != me.user_id).first()
        if exists:
            raise HTTPException(status_code=400, detail="NICKNAME_DUPLICATE")
        me.nickname = data["nickname"]
    if "introduction" in data:
        me.introduction = data["introduction"]
    if "image_url" in data:
        me.image_url = data["image_url"]
    if "category" in data:
        me.category = data["category"]

    me.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(me)
    return me
