from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, or_
from datetime import datetime, timezone
from pydantic import BaseModel

from app.core.db import get_db
from app.models.posting import Posting, PostingImage
from app.models.favorite import Favorite
from app.models.user import User
from app.schemas.posting import (
    PostingCreateIn, PostingUpdateIn, PostingOut, PostingListItem, PageOut
)
from app.core.auth import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/postings", tags=["postings"])


# ---------- helpers ----------
def to_posting_out(p: Posting, is_owner: Optional[bool] = None, is_favorite: Optional[bool] = None) -> PostingOut:
    def iso(dt):
        if not dt:
            return None
        s = dt.isoformat()
        return s.replace("+00:00", "Z")

    return PostingOut(
        posting_id=p.id,
        seller_id=p.seller_id,
        title=p.title,
        price=p.price,
        content=p.content,
        category=p.category,
        view_count=p.view_count,
        like_count=p.like_count,
        chat_count=p.chat_count,
        created_at=p.created_at,
        updated_at=p.updated_at,
        images=[img.url for img in (p.images or [])],
        is_owner=is_owner,
        is_favorite=is_favorite,
    )


def to_list_item(p: Posting, is_favorite: bool = False) -> PostingListItem:
    thumb = p.images[0].url if p.images else None
    return PostingListItem(
        posting_id=p.id,
        seller_id=p.seller_id,
        title=p.title,
        price=p.price,
        content=p.content,
        category=p.category,
        created_at=p.created_at,
        like_count=p.like_count,
        chat_count=p.chat_count,
        view_count=p.view_count,
        thumbnail=thumb,
        is_favorite=is_favorite,
    )


# ---------- 1) 게시물 생성 ----------
@router.post("", response_model=PostingOut, status_code=200)
def create_posting(
    body: PostingCreateIn,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    p = Posting(
        seller_id=me.user_id,
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
    return to_posting_out(p, is_owner=True, is_favorite=False)


# ---------- 2) 전체 리스트 조회 (토큰 불필요) ----------
@router.get("", response_model=PageOut)
def list_postings(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    sort: str = Query("latest", regex="^(latest|likeCount|chatCount|viewCount)$"),
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    me: Optional[User] = Depends(get_current_user_optional),   # ✅ optional
):
    q = select(Posting)

    # 검색/카테고리
    if keyword:
        like = f"%{keyword}%"
        q = q.where(or_(Posting.title.ilike(like), Posting.content.ilike(like)))
    if category:
        q = q.where(Posting.category == category)

    # ✅ 토큰 있으면 내 게시물 제외
    if me:
        q = q.where(Posting.seller_id != me.user_id)

    sort_map = {
        "latest": desc(Posting.created_at),
        "likeCount": desc(Posting.like_count),
        "chatCount": desc(Posting.chat_count),
        "viewCount": desc(Posting.view_count),
    }
    q = q.order_by(sort_map.get(sort, desc(Posting.created_at)))

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.execute(q.offset((page - 1) * size).limit(size)).scalars().all()

    # (옵션) 토큰 있으면 is_favorite 계산 — 필요 없으면 이 블록 삭제해도 됨
    fav_ids: set[int] = set()
    if me and rows:
        post_ids = [p.id for p in rows]
        fav_ids = set(
            db.execute(
                select(Favorite.posting_id)
                .where(Favorite.user_id == me.user_id, Favorite.posting_id.in_(post_ids))
            ).scalars().all()
        )

    data: List[PostingListItem] = [
        to_list_item(p, is_favorite=(p.id in fav_ids if me else False)) for p in rows
    ]
    return PageOut(page=page, size=size, total=total, data=data)



# ---------- 3) 내 게시물 ----------
@router.get("/my", response_model=PageOut)
def my_postings(
    status_filter: str = Query(..., alias="status", regex="^(selling|sold|purchased|favorite)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    q = select(Posting).where(Posting.seller_id == me.user_id)

    if status_filter == "selling":
        pass
    elif status_filter == "favorite":
        raise HTTPException(501, "favorite 목록 API는 추후 구현 예정")
    elif status_filter in ("sold", "purchased"):
        raise HTTPException(501, "거래 상태 API는 추후 구현 예정")

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.execute(q.order_by(desc(Posting.created_at)).offset((page-1)*size).limit(size)).scalars().all()

    data = [to_list_item(p, is_favorite=False) for p in rows]
    return PageOut(page=page, size=size, total=total, data=data)


# ---------- 4) 특정 유저의 게시물 (특정 글 제외 지원) ----------
@router.get("/user/{user_id}", response_model=PageOut)
def postings_by_user(
    user_id: int = Path(..., ge=1),
    exclude_posting_id: Optional[int] = Query(None, alias="postingId"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = select(Posting).where(Posting.seller_id == user_id)
    if exclude_posting_id is not None:
        q = q.where(Posting.id != exclude_posting_id)

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.execute(q.order_by(desc(Posting.created_at)).offset((page-1)*size).limit(size)).scalars().all()
    data = [to_list_item(p, is_favorite=False) for p in rows]
    return PageOut(page=page, size=size, total=total, data=data)


# ---------- 5) 게시물 상세 (토큰 불필요) ----------


# ---------- 5) 게시물 상세 (토큰 optional) ----------
@router.get("/{posting_id}", response_model=PostingOut)
def get_posting(
    posting_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    me: Optional[User] = Depends(get_current_user_optional),  # ✅ optional
):
    p = db.get(Posting, posting_id)
    if not p:
        raise HTTPException(status_code=404, detail="게시물 없음")

    # 조회수 증가
    p.view_count += 1
    p.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(p)

    # ✅ 토큰 있으면 is_owner / is_favorite 계산
    is_owner = bool(me and p.seller_id == me.user_id)
    is_favorite = False
    if me and not is_owner:
        is_favorite = db.query(
            db.query(Favorite)
            .filter(Favorite.user_id == me.user_id, Favorite.posting_id == p.id)
            .exists()
        ).scalar()

    return to_posting_out(p, is_owner=is_owner, is_favorite=is_favorite)


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
    if p.seller_id != me.user_id:
        raise HTTPException(403, "권한 없음")

    if body.title is not None:
        p.title = body.title
    if body.price is not None:
        p.price = body.price
    if body.content is not None:
        p.content = body.content
    if body.category is not None:
        p.category = body.category

    if body.images is not None:
        p.images.clear()
        db.flush()
        for url in body.images:
            db.add(PostingImage(posting_id=p.id, url=str(url)))

    db.commit()
    db.refresh(p)
    return to_posting_out(p, is_owner=True, is_favorite=False)


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
    if p.seller_id != me.user_id:
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
    likeCount: int

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
