from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.db import get_db
from app.models.favorite import Favorite
from app.models.posting import Posting
from app.models.user import User
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/postings", tags=["favorites"])


@router.put("/{posting_id}/favorite")
def toggle_favorite(
    posting_id: int,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    posting = db.get(Posting, posting_id)
    if not posting:
        raise HTTPException(status_code=404, detail="게시물 없음")

    f = db.query(Favorite).filter(
        Favorite.user_id == me.user_id,
        Favorite.posting_id == posting_id
    ).first()

    added = False
    if f:
        db.delete(f)
        posting.like_count = max(0, posting.like_count - 1)
    else:
        nf = Favorite(user_id=me.user_id, posting_id=posting_id)
        db.add(nf)
        posting.like_count = posting.like_count + 1
        added = True

    hard = db.query(func.count(Favorite.user_id)).filter(Favorite.posting_id == posting_id).scalar()
    if posting.like_count != hard:
        posting.like_count = hard

    db.commit()
    db.refresh(posting)
    return {
        "postingId": posting_id,
        "favorited": added,
        "likeCount": posting.like_count
    }
