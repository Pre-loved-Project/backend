from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.db import get_db
from app.models.favorite import Favorite
from app.models.posting import Posting
from app.models.user import User
from app.core.auth import get_current_user
from pydantic import BaseModel
from datetime import datetime, timezone

router = APIRouter(prefix="/api/postings", tags=["favorites"])


# ---------- 8) 즐겨찾기 토글 ----------
class FavoriteToggleIn(BaseModel):
    favorite: bool


class FavoriteToggleOut(BaseModel):
    message: str
    postingId: int
    favorite: bool
    updatedAt: str
    likeCount: int

@router.put("/{posting_id}/favorite", response_model=FavoriteToggleOut)
def toggle_favorite(
    posting_id: int,
    body: FavoriteToggleIn,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    p = db.get(Posting, posting_id)
    if not p:
        raise HTTPException(404, "게시물 없음")

    fav = db.query(Favorite).filter(
        Favorite.user_id == me.user_id,
        Favorite.posting_id == p.id
    ).first()

    # 변경 수행
    if body.favorite:
        if not fav:
            db.add(Favorite(user_id=me.user_id, posting_id=p.id))
            # (선택) 즉시 증가시키되 어차피 아래 하드동기화로 확정됨
            p.like_count += 1
    else:
        if fav:
            db.delete(fav)
            p.like_count = max(0, p.like_count - 1)

    # ✅ 여기 추가: 세션에 쌓인 변경 내용을 DB에 flush
    db.flush()

    # ✅ 하드 동기화 (이제 방금 변경이 카운트에 반영됨)
    hard = db.query(func.count(Favorite.user_id))\
             .filter(Favorite.posting_id == p.id)\
             .scalar()
    if p.like_count != hard:
        p.like_count = hard

    db.commit()
    db.refresh(p)

    msg = "즐겨찾기가 등록되었습니다." if body.favorite else "즐겨찾기가 취소되었습니다."
    now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

    return FavoriteToggleOut(
        message=msg,
        postingId=p.id,
        favorite=body.favorite,
        updatedAt=now,
        likeCount=p.like_count,
    )