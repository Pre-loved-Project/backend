# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.db import Base, engine

# 모델: 반드시 PostingImage까지 import 해 테이블이 생성되게!
from app.models.user import User
from app.models.posting import Posting, PostingImage
from app.models.favorite import Favorite
from app.models.consent import UserConsent
from app.models.email_verification import EmailVerification

# 모든 모델 import가 끝난 뒤 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pre-loved API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터
from app.routers import users, auth, postings, favorites, predict
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(postings.router)    # ← 파일명이 postings.py일 때
app.include_router(favorites.router)
app.include_router(predict.router)

@app.get("/health")
def health():
    return {"status": "ok"}
