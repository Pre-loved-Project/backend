# app/routers/posting.py

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import Optional

from app.core.db import get_db
from app.core.auth import get_current_user
from app.schemas.posting import (
    PostingCreateIn,
    PostingUpdateIn,
    PostingOut,
    PostingListItemOut,
    PageOut,
    FavoriteToggleIn,
    FavoriteToggleOut,
)
from app.services.postings import (
    create_posting,
    list_postings,
    get_posting,
    update_posting,
    delete_posting,
    set_favorite,
)
from app.models.posting import Posting

router = APIRouter(prefix="/api/postings", tags=["postings"])

def _uid(u) -> int:
    for k in ("user_id", "userId", "id"):
        v = getattr(u, k, None)
        if v is not None:
            return int(v)
    raise HTTPException(status_code=401, detail="invalid_token")

@router.post("", response_model=PostingOut, status_code=200)
def create_posting_api(
    body: PostingCreateIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    p = create_posting(
        db,
        seller_id=_uid(user),
        title=body.title,
        price=body.price,
        content=body.content,
        images=[str(u) for u in body.images],
    )
    return p

@router.get("", response_model=PageOut[PostingListItemOut])
def list_postings_api(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    includeContent: Optional[bool] = Query(False),
    db: Session = Depends(get_db),
):
    rows, total = list_postings(db, page, size, include_content=bool(includeContent))
    data = []
    for r in rows:
        thumb = r.images[0].url if r.images else None
        data.append(
            PostingListItemOut(
                posting_id=r.posting_id,
                title=r.title,
                price=r.price,
                seller_id=r.seller_id,
                created_at=r.created_at,
                like_count=r.like_count,
                chat_count=r.chat_count,
                view_count=r.view_count,
                thumbnail=thumb,
                content=r.content,
            )
        )
    return dict(page=page, size=size, total=total, data=data)

@router.get("/{postingId}", response_model=PostingOut)
def get_posting_api(
    postingId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    p = get_posting(db, postingId, inc_view=True)
    if not p:
        raise HTTPException(status_code=404, detail="Posting not found")
    return p

@router.patch("/{postingId}", response_model=PostingOut)
def update_posting_api(
    body: PostingUpdateIn,
    postingId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    p = db.query(Posting).filter(Posting.posting_id == postingId).first()
    if not p:
        raise HTTPException(status_code=404, detail="Posting not found")
    if p.seller_id != _uid(user) and not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Forbidden")
    p = update_posting(
        db,
        p,
        title=body.title,
        price=body.price,
        content=body.content,
        images=[str(u) for u in body.images] if body.images is not None else None,
    )
    return p

@router.delete("/{postingId}")
def delete_posting_api(
    postingId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    p = db.query(Posting).filter(Posting.posting_id == postingId).first()
    if not p:
        raise HTTPException(status_code=404, detail="Posting not found")
    if p.seller_id != _uid(user) and not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Forbidden")
    pid = delete_posting(db, p)
    return dict(postingId=pid)

@router.put("/{postingId}/favorite", response_model=FavoriteToggleOut)
def toggle_favorite_api(
    body: FavoriteToggleIn,
    postingId: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    p = db.query(Posting).filter(Posting.posting_id == postingId).first()
    if not p:
        raise HTTPException(status_code=404, detail="Posting not found")
    uid = _uid(user)
    result = set_favorite(db, uid, postingId, body.favorite)
    msg = "즐겨찾기가 등록되었습니다." if result else "즐겨찾기가 취소되었습니다."
    return dict(message=msg, postingId=postingId, userId=uid, favorite=result, updatedAt=p.updated_at)
