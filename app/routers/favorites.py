from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.favorite import Favorite
from app.models.user import User
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/postings", tags=["favorites"])

@router.put("/{postingId}/favorite")
def toggle_favorite(
    postingId: int,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    f = db.query(Favorite).filter(
    Favorite.userId == me.userId, 
    Favorite.postingId == postingId
    ).first()


    if f:
        db.delete(f)
        db.commit()
        return {"postingId": postingId, "favorited": False}

    nf = Favorite(userId=me.id, postingId=postingId)
    db.add(nf)
    db.commit()
    return {"postingId": postingId, "favorited": True}
