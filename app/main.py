from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.db import Base, engine
from app.core.config import settings

# ✅ 1) FastAPI 앱 생성
app = FastAPI(title="Pre-loved API")

# ✅ 2) 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ 3) DB 모델 import & create_all
from app.models.user import User
from app.models.posting import Posting, PostingImage
from app.models.favorite import Favorite
from app.models.consent import UserConsent
from app.models.email_verification import EmailVerification

print("### DB URL =", settings.DATABASE_URL)
print("### tables BEFORE:", list(Base.metadata.tables.keys()))
Base.metadata.create_all(bind=engine)
print("### tables AFTER :", list(Base.metadata.tables.keys()))
with engine.connect() as conn:
    rows = conn.execute(text("PRAGMA database_list;")).all()
    print("### PRAGMA database_list:", rows)

# ✅ 4) 라우터 등록
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.postings import router as postings_router
from app.routers.favorites import router as favorites_router
from app.routers.predict import router as predict_router
from app.routers.image import router as image_router  # ← 여기!

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(postings_router)
app.include_router(favorites_router)
app.include_router(predict_router)
app.include_router(image_router)  # ← app 선언 이후에 등록해야 함!

# ✅ 5) 라우트 확인 로그
print("### ROUTES (method, path)")
for r in app.routes:
    try:
        print("   ", getattr(r, "methods", None), getattr(r, "path", None))
    except Exception:
        pass
