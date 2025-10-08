#app/services/posting.py

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from datetime import datetime
from app.models.posting import Posting, PostingImage
from app.models.favorite import Favorite

def create_posting(db: Session, seller_id: int, title: str, price: int, content: str, images: List[str]) -> Posting:
    p = Posting(seller_id=seller_id, title=title, price=price, content=content)
    db.add(p)
    db.flush()
    for i, u in enumerate(images):
        db.add(PostingImage(posting_id=p.posting_id, url=str(u), ord=i))
    db.commit()
    db.refresh(p)
    return p

def list_postings(db: Session, page: int, size: int, include_content: bool) -> Tuple[List[Posting], int]:
    q = db.query(Posting).order_by(Posting.posting_id.desc())
    total = q.count()
    rows = q.offset((page - 1) * size).limit(size).all()
    if not include_content:
        for r in rows:
            r.content = None
    return rows, total

def get_posting(db: Session, posting_id: int, inc_view: bool) -> Optional[Posting]:
    p = db.query(Posting).filter(Posting.posting_id == posting_id).first()
    if p and inc_view:
        p.view_count += 1
        p.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(p)
    return p

def update_posting(db: Session, posting: Posting, title: Optional[str], price: Optional[int], content: Optional[str], images: Optional[List[str]]) -> Posting:
    if title is not None:
        posting.title = title
    if price is not None:
        posting.price = price
    if content is not None:
        posting.content = content
    posting.updated_at = datetime.utcnow()
    if images is not None:
        db.query(PostingImage).filter(PostingImage.posting_id == posting.posting_id).delete()
        for i, u in enumerate(images):
            db.add(PostingImage(posting_id=posting.posting_id, url=str(u), ord=i))
    db.commit()
    db.refresh(posting)
    return posting

def delete_posting(db: Session, posting: Posting) -> int:
    pid = posting.posting_id
    db.delete(posting)
    db.commit()
    return pid

def set_favorite(db: Session, user_id: int, posting_id: int, favorite: bool) -> bool:
    ex = db.query(Favorite).filter(Favorite.user_id == user_id, Favorite.posting_id == posting_id).first()
    if favorite and not ex:
        db.add(Favorite(user_id=user_id, posting_id=posting_id))
        db.commit()
        return True
    if not favorite and ex:
        db.delete(ex)
        db.commit()
        return False
    return bool(ex)
