from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.core.db import get_db
from app.models.posting import Posting
from app.models.user import User
from app.schemas.posting import PostingCreate, PostingResp
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/postings", tags=["postings"])

@router.post("", response_model=PostingResp, status_code=201)
def create_posting(
    payload: PostingCreate,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    p = Posting(
        sellerId=me.id,  # 여기 userId 대신 id 확인 필요
        title=payload.title,
        content=payload.content,
        price=payload.price,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

@router.get("", response_model=List[PostingResp])
def list_postings(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, le=100),
):
    q = db.query(Posting).order_by(Posting.createdAt.desc(), Posting.postingId.desc())
    items = q.offset((page - 1) * size).limit(size).all()
    return items

@router.get("/{postingId}", response_model=PostingResp)
def get_posting(postingId: int, db: Session = Depends(get_db)):
    p = db.query(Posting).filter(Posting.postingId == postingId).first()
    if not p:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    return p
