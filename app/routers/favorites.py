# app/routers/favorite.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.favorite import Favorite
from app.models.user import User
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/postings", tags=["favorites"])

@router.put("/{posting_id}/favorite")
def toggle_favorite(
    posting_id: int,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    f = db.query(Favorite).filter(
        Favorite.user_id == me.user_id,
        Favorite.posting_id == posting_id
    ).first()

    if f:
        db.delete(f)
        db.commit()
        return {"postingId": posting_id, "favorited": False}

    nf = Favorite(user_id=me.user_id, posting_id=posting_id)
    db.add(nf)
    db.commit()
    return {"postingId": posting_id, "favorited": True}
