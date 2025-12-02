from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, or_
from datetime import datetime, timezone

from app.core.db import get_db
from app.models.posting import Posting, PostingImage
from app.models.favorite import Favorite
from app.models.user import User
from app.models.chat import ChatRoom
from app.schemas.posting import (
    PostingCreateIn, PostingUpdateIn, PostingOut, PostingListItem, PageOut, ChatExistOut
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
        status=p.status,
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
        status=p.status,
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
    # ----- 판매중 / 판매완료(내가 판매자) -----
    if status_filter == "selling":
        q = (
            select(Posting)
            .where(
                Posting.seller_id == me.user_id,
                Posting.status == "SELLING"
            )
        )

    elif status_filter == "sold":
        q = (
            select(Posting)
            .where(
                Posting.seller_id == me.user_id,
                Posting.status == "SOLD"
            )
        )

    # ----- favorite (내가 즐겨찾기한 게시물) -----
    elif status_filter == "favorite":
        q = (
            select(Posting)
            .join(Favorite, Favorite.posting_id == Posting.id)
            .where(Favorite.user_id == me.user_id)
        )

    # ----- purchased (내가 구매한 거래) -----
    elif status_filter == "purchased":
        q = (
            select(Posting)
            .join(ChatRoom, ChatRoom.posting_id == Posting.id)
            .where(
                ChatRoom.buyer_id == me.user_id,
                ChatRoom.status == "COMPLETED"
            )
        )

    else:
        raise HTTPException(400, "Invalid status")

    # ----- 페이징 -----
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = (
        db.execute(
            q.order_by(desc(Posting.created_at))
            .offset((page - 1) * size)
            .limit(size)
        )
        .scalars()
        .all()
    )

    # ----- 즐겨찾기 여부 계산 -----
    posting_ids = [p.id for p in rows]
    fav_map = {
        f.posting_id: True
        for f in db.query(Favorite)
        .filter(Favorite.user_id == me.user_id, Favorite.posting_id.in_(posting_ids))
        .all()
    }

    # ----- list item 변환 -----
    data = [
        to_list_item(p, is_favorite=fav_map.get(p.id, False))
        for p in rows
    ]

    return PageOut(
        page=page,
        size=size,
        total=total,
        data=data
    )



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

@router.get("/{posting_id}/chat", response_model=ChatExistOut)
def check_chat_exist(
    posting_id: int = Path(..., description="대상 게시글 ID"),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    """
    해당 게시물에 대해 현재 로그인한 사용자가 가진 채팅방이 존재하는지 확인
    """

    # 1) 게시글 존재 여부 확인 (없으면 404)
    posting = db.query(Posting).filter(Posting.id == posting_id).first()
    if not posting:
        raise HTTPException(status_code=404, detail="posting_not_found")  # 명세 404

    # 2) 현재 로그인한 유저(me)가 이 게시물에 대해 만든 채팅방이 있는지 확인
    room = (
        db.query(ChatRoom)
        .filter(
            ChatRoom.posting_id == posting_id,
            ChatRoom.buyer_id == me.user_id,  # create_chat에서 쓰던 조건과 동일
        )
        .first()
    )

    if room:
        return ChatExistOut(isExist=True, chatId=room.id)
    else:
        return ChatExistOut(isExist=False, chatId=None)