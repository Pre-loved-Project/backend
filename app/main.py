from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware   
from app.core.db import Base, engine

# 모델 임포트
from app.models.user import User
from app.models.posting import Posting
from app.models.favorite import Favorite
from app.models.consent import UserConsent
from app.models.email_verification import EmailVerification

# 라우터 임포트
from app.routers import users, auth, postings, favorites, predict


# DB 테이블 생성
Base.metadata.create_all(bind=engine)

# FastAPI 앱 생성
app = FastAPI(title="Pre-loved API")

# CORS 설정 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       
    allow_credentials=True,
    allow_methods=["*"],        
    allow_headers=["*"],        
)

# 라우터 등록
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(postings.router)
app.include_router(favorites.router)
app.include_router(predict.router)

@app.get("/health")
def health():
    return {"status": "ok"}