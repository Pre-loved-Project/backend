#app/routers/postings.py

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, or_
from app.core.db import get_db
from app.models.posting import Posting, PostingImage
from app.models.user import User
from app.schemas.posting import (
    PostingCreateIn, PostingUpdateIn, PostingOut, PostingListItem, PageOut
)
from app.core.security import get_current_user  # JWT 디펜던시 (존재 가정)
from pydantic import BaseModel                # ✅ FavoriteToggleIn/Out용
from datetime import datetime, timezone       # ✅ updatedAt 만들 때 사용

router = APIRouter(prefix="/api/postings", tags=["postings"])

# ---------- helpers ----------

def to_posting_out(p: Posting, is_owner: Optional[bool] = None) -> PostingOut:
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
        createdAt=p.created_at.isoformat().replace("+00:00","Z"),
        updatedAt=p.updated_at.isoformat().replace("+00:00","Z"),
        images=[img.url for img in (p.images or [])],
        isOwner=is_owner,
    )

def to_list_item(p: Posting) -> PostingListItem:
    thumb = p.images[0].url if p.images else None
    return PostingListItem(
        postingId=p.id,
        sellerId=p.seller_id,
        title=p.title,
        price=p.price,
        content=p.content,  # 필요 시 None으로 바꿔도 됨
        category=p.category,
        createdAt=p.created_at.isoformat().replace("+00:00","Z"),
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
        seller_id=me.id,
        title=body.title,
        price=body.price,
        content=body.content,
        category=body.category,  # ✅ NEW
    )
    db.add(p)
    db.flush()  # id 확보

    for url in body.images:
        db.add(PostingImage(posting_id=p.id, url=str(url)))

    db.commit()
    db.refresh(p)
    return to_posting_out(p, is_owner=True)

# ---------- 2) 전체 리스트 조회 (page,size,sort,keyword,category) ----------

@router.get("", response_model=PageOut)
def list_postings(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    sort: str = Query("latest", regex="^(latest|likeCount|chatCount|viewCount)$"),
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = select(Posting).options()  # relationship은 모델에 selectin 설정

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

# ---------- 3) 현재 유저 관련 게시물 /api/postings/my?status=... ----------

@router.get("/my", response_model=PageOut)
def my_postings(
    status_filter: str = Query(..., alias="status", regex="^(selling|sold|purchased|favorite)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    # 최소 구현: selling(내가 올린 것)만 정확히, 나머지는 TODO로 둠
    q = select(Posting).where(Posting.seller_id == me.id)

    # sold/purchased/favorite 구현은 거래/즐겨찾기 테이블 연동 필요 (추후 보강)
    if status_filter == "selling":
        pass  # 상태 컬럼이 있다면 여기서 필터
    elif status_filter == "favorite":
        # Favorite 테이블 조인 필요 — 스키마에 맞게 조인 구현
        raise HTTPException(501, "favorite 목록 API는 이후 Favorite 테이블 연동 시 구현")
    elif status_filter in ("sold", "purchased"):
        raise HTTPException(501, "거래 상태(sold/purchased) 필터는 거래 테이블 연동 시 구현")

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.execute(q.order_by(desc(Posting.created_at)).offset((page-1)*size).limit(size)).scalars().all()

    return PageOut(page=page, size=size, total=total, data=[to_list_item(p) for p in rows])

# ---------- 4) 특정 유저 전체 게시물 ----------

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

# ---------- 5) 특정 ID 게시물 조회 (조회수 +1, isOwner 포함) ----------

@router.get("/{posting_id}", response_model=PostingOut)
def get_posting(
    posting_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    me: Optional[User] = Depends(get_current_user)  # 미인증이면 미들웨어에서 401이면 됨, 혹은 Optional 처리
):
    p = db.get(Posting, posting_id)
    if not p:
        raise HTTPException(status_code=404, detail="게시물 없음")

    # 조회수 +1
    p.view_count += 1
    db.add(p)
    db.commit()
    db.refresh(p)

    is_owner = (me.id == p.seller_id) if me else False
    return to_posting_out(p, is_owner=is_owner)

# ---------- 6) 특정 ID 게시물 수정 (category 포함) ----------

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
    if p.seller_id != me.id:
        raise HTTPException(403, "권한 없음")

    if body.title is not None: p.title = body.title
    if body.price is not None: p.price = body.price
    if body.content is not None: p.content = body.content
    if body.category is not None: p.category = body.category  # ✅ NEW

    if body.images is not None:
        # 전량 교체
        p.images.clear()
        db.flush()
        for url in body.images:
            db.add(PostingImage(posting_id=p.id, url=str(url)))

    db.add(p)
    db.commit()
    db.refresh(p)
    return to_posting_out(p, is_owner=True)

# ---------- 7) 특정 ID 게시물 삭제 ----------

@router.delete("/{posting_id}", status_code=200)
def delete_posting(
    posting_id: int,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    p = db.get(Posting, posting_id)
    if not p:
        raise HTTPException(404, "게시물 없음")
    if p.seller_id != me.id:
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
    # Favorite 테이블 스키마에 맞게 upsert 로직 구현 필요
    # 여기선 형식만 맞춰 응답 (실구현 시에 교체)
    p = db.get(Posting, posting_id)
    if not p:
        raise HTTPException(404, "게시물 존재하지 않음")

    # TODO: Favorite upsert
    msg = "즐겨찾기가 등록되었습니다." if body.favorite else "즐겨찾기가 취소되었습니다."
    return FavoriteToggleOut(
        message=msg,
        postingId=posting_id,
        favorite=body.favorite,
        updatedAt=func.now().isoformat() if hasattr(func.now(), "isoformat") else "2025-09-13T16:00:00Z",
    )
