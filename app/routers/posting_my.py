from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.posting import Posting, PostingStatus, PostingImage
from app.models.favorite import Favorite
from app.models.chat import ChatRoom
from app.schemas.posting_my import MyPostingsOut, MyPostingItemOut

router = APIRouter(prefix="/api/postings", tags=["postings"])


@router.get("/my", response_model=MyPostingsOut)
def get_my_postings(
    status_param: str = Query(..., alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed_status = {"selling", "sold", "purchased", "favorite"}
    if status_param not in allowed_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="INVALID_STATUS",
        )

    base_query = db.query(Posting)

    if status_param == "selling":
        base_query = base_query.filter(
            Posting.seller_id == current_user.userId,
            Posting.status == PostingStatus.SELLING,
        )
    elif status_param == "sold":
        base_query = base_query.filter(
            Posting.seller_id == current_user.userId,
            Posting.status == PostingStatus.COMPLETED,
        )
    elif status_param == "purchased":
        base_query = (
            base_query.join(ChatRoom, ChatRoom.posting_id == Posting.id)
            .filter(
                ChatRoom.buyer_id == current_user.userId,
                ChatRoom.status == "COMPLETED",
            )
        )
    elif status_param == "favorite":
        base_query = (
            base_query.join(Favorite, Favorite.posting_id == Posting.id)
            .filter(
                Favorite.user_id == current_user.userId,
                Favorite.is_favorite.is_(True),
            )
        )

    total = base_query.distinct().count()

    postings = (
        base_query.order_by(Posting.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    posting_ids = [p.id for p in postings]
    thumbnails_subq = (
        db.query(
            PostingImage.posting_id,
            func.min(PostingImage.id).label("min_id"),
        )
        .filter(PostingImage.posting_id.in_(posting_ids))
        .group_by(PostingImage.posting_id)
        .subquery()
    )

    thumbnails = (
        db.query(PostingImage)
        .join(
            thumbnails_subq,
            (thumbnails_subq.c.posting_id == PostingImage.posting_id)
            & (thumbnails_subq.c.min_id == PostingImage.id),
        )
        .all()
    )
    thumb_map = {img.posting_id: img.image_url for img in thumbnails}

    data = []
    for p in postings:
        item = MyPostingItemOut(
            postingId=p.id,
            sellerId=p.seller_id,
            title=p.title,
            price=p.price,
            content=p.content,
            category=p.category,
            createdAt=p.created_at,
            likeCount=p.like_count,
            chatCount=p.chat_count,
            viewCount=p.view_count,
            thumbnail=thumb_map.get(p.id),
        )
        data.append(item)

    return MyPostingsOut(page=page, size=size, total=total, data=data)
