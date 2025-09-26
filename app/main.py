from fastapi import FastAPI
from app.core.db import Base, engine

# 모델 임포트 (테이블 자동 생성용)
from app.models.user import User
from app.models.posting import Posting
from app.models.favorite import Favorite

# 👇 consent / email_verification 둘 다 쓸 계획이면 유지
from app.models.consent import UserConsent
from app.models.email_verification import EmailVerification

# 라우터 임포트
from app.routers import users, auth, postings, favorites, predict


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pre-loved API")
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(postings.router)
app.include_router(favorites.router)
app.include_router(predict.router)

@app.get("/health")
def health():
    return {"status": "ok"}
