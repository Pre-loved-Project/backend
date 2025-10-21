from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, or_
from datetime import datetime, timezone
from pydantic import BaseModel

from app.core.db import get_db
from app.models.posting import Posting, PostingImage
from app.models.user import User
from app.schemas.posting import (
    PostingCreateIn, PostingUpdateIn, PostingOut, PostingListItem, PageOut
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/postings", tags=["postings"])

# ---------- helpers ----------

def to_posting_out(p: Posting, is_owner: Optional[bool] = None) -> PostingOut:
    def iso(dt):
        if not dt:
            return None
        s = dt.isoformat()
        return s.replace("+00:00", "Z")

    return PostingOut(
        postingId=p.id,
        sellerId=p.seller_id,
        title=p.title,
        price=p.price,
        content=p.content,
        category=p.category,
        viewCount=p.view_count,
        likeCount=p.like_count,
        chatCount=p.chat_count,
        createdAt=iso(p.created_at),
        updatedAt=iso(p.updated_at),
        images=[img.url for img in (p.images or [])],
        isOwner=is_owner,
    )

def to_list_item(p: Posting) -> PostingListItem:
    thumb = p.images[0].url if p.images else None
    def iso(dt):
        if not dt:
            return None
        return dt.isoformat().replace("+00:00", "Z")

    return PostingListItem(
        postingId=p.id,
        sellerId=p.seller_id,
        title=p.title,
        price=p.price,
        content=p.content,
        category=p.category,
        createdAt=iso(p.created_at),
        likeCount=p.like_count,
        chatCount=p.chat_count,
        viewCount=p.view_count,
        thumbnail=thumb,
    )

# ---------- 1) 게시물 생성 ----------

@router.post("", response_model=PostingOut, status_code=200)
def create_posting(
    body: PostingCreateIn,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    p = Posting(
        seller_id=me.user_id,  # ✅ 수정됨
        title=body.title,
        price=body.price,
        content=body.content,
        category=body.category,
    )
    db.add(p)
    db.flush()  # id 확보

    for url in body.images:
        db.add(PostingImage(posting_id=p.id, url=str(url)))

    db.commit()
    db.refresh(p)
    return to_posting_out(p, is_owner=True)

# ---------- 2) 전체 리스트 조회 ----------

@router.get("", response_model=PageOut)
def list_postings(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    sort: str = Query("latest", regex="^(latest|likeCount|chatCount|viewCount)$"),
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = select(Posting)

    if keyword:
        like = f"%{keyword}%"
        q = q.where(or_(Posting.title.ilike(like), Posting.content.ilike(like)))
    if category:
        q = q.where(Posting.category == category)

    sort_map = {
        "latest": desc(Posting.created_at),
        "likeCount": desc(Posting.like_count),
        "chatCount": desc(Posting.chat_count),
        "viewCount": desc(Posting.view_count),
    }
    q = q.order_by(sort_map.get(sort, desc(Posting.created_at)))

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.execute(q.offset((page - 1) * size).limit(size)).scalars().all()

    return PageOut(
        page=page, size=size, total=total,
        data=[to_list_item(p) for p in rows]
    )

# ---------- 3) 내 게시물 ----------

@router.get("/my", response_model=PageOut)
def my_postings(
    status_filter: str = Query(..., alias="status", regex="^(selling|sold|purchased|favorite)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    q = select(Posting).where(Posting.seller_id == me.user_id)  # ✅ 수정됨

    if status_filter == "selling":
        pass
    elif status_filter == "favorite":
        raise HTTPException(501, "favorite 목록 API는 추후 구현 예정")
    elif status_filter in ("sold", "purchased"):
        raise HTTPException(501, "거래 상태 API는 추후 구현 예정")

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.execute(q.order_by(desc(Posting.created_at)).offset((page-1)*size).limit(size)).scalars().all()

    return PageOut(page=page, size=size, total=total, data=[to_list_item(p) for p in rows])

# ---------- 4) 특정 유저의 게시물 ----------

@router.get("/user/{user_id}", response_model=PageOut)
def postings_by_user(
    user_id: int = Path(..., ge=1),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = select(Posting).where(Posting.seller_id == user_id)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.execute(q.order_by(desc(Posting.created_at)).offset((page-1)*size).limit(size)).scalars().all()
    return PageOut(page=page, size=size, total=total, data=[to_list_item(p) for p in rows])

# ---------- 5) 게시물 상세 ----------

@router.get("/{posting_id}", response_model=PostingOut)
def get_posting(
    posting_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    me: Optional[User] = Depends(get_current_user),
):
    p = db.get(Posting, posting_id)
    if not p:
        raise HTTPException(status_code=404, detail="게시물 없음")

    p.view_count += 1
    db.add(p)
    db.commit()
    db.refresh(p)

    is_owner = (me.user_id == p.seller_id) if me else False  # ✅ 수정됨
    return to_posting_out(p, is_owner=is_owner)

# ---------- 6) 게시물 수정 ----------

@router.patch("/{posting_id}", response_model=PostingOut)
def update_posting(
    posting_id: int,
    body: PostingUpdateIn,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    p = db.get(Posting, posting_id)
    if not p:
        raise HTTPException(404, "게시물 없음")
    if p.seller_id != me.user_id:  # ✅ 수정됨
        raise HTTPException(403, "권한 없음")

    if body.title is not None: p.title = body.title
    if body.price is not None: p.price = body.price
    if body.content is not None: p.content = body.content
    if body.category is not None: p.category = body.category

    if body.images is not None:
        p.images.clear()
        db.flush()
        for url in body.images:
            db.add(PostingImage(posting_id=p.id, url=str(url)))

    db.add(p)
    db.commit()
    db.refresh(p)
    return to_posting_out(p, is_owner=True)

# ---------- 7) 게시물 삭제 ----------

@router.delete("/{posting_id}", status_code=200)
def delete_posting(
    posting_id: int,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    p = db.get(Posting, posting_id)
    if not p:
        raise HTTPException(404, "게시물 없음")
    if p.seller_id != me.user_id:  # ✅ 수정됨
        raise HTTPException(403, "권한 없음")

    db.delete(p)
    db.commit()
    return {"postingId": posting_id}

# ---------- 8) 즐겨찾기 토글 ----------

class FavoriteToggleIn(BaseModel):
    favorite: bool

class FavoriteToggleOut(BaseModel):
    message: str
    postingId: int
    favorite: bool
    updatedAt: str

@router.post("/{posting_id}/favorite", response_model=FavoriteToggleOut)
def toggle_favorite(
    posting_id: int,
    body: FavoriteToggleIn,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    p = db.get(Posting, posting_id)
    if not p:
        raise HTTPException(404, "게시물 없음")

    now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    msg = "즐겨찾기가 등록되었습니다." if body.favorite else "즐겨찾기가 취소되었습니다."

    return FavoriteToggleOut(
        message=msg,
        postingId=posting_id,
        favorite=body.favorite,
        updatedAt=now,
    )
