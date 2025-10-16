from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.db import Base, engine
from app.core.config import settings

# ✅ 1) FastAPI 앱 생성
app = FastAPI(title="Pre-loved API")

# ✅ 2) CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ 3) DB 모델 import & 테이블 생성
from app.models.user import User
from app.models.posting import Posting, PostingImage
from app.models.favorite import Favorite
from app.models.consent import UserConsent
from app.models.email_verification import EmailVerification

print("### DB URL =", settings.DATABASE_URL)
print("### tables BEFORE:", list(Base.metadata.tables.keys()))
Base.metadata.create_all(bind=engine)
print("### tables AFTER :", list(Base.metadata.tables.keys()))

# ✅ 3-1) DB 연결 진단 로그
backend = engine.url.get_backend_name()
try:
    with engine.connect() as conn:
        if backend == "sqlite":
            rows = conn.execute(text("PRAGMA database_list;")).all()
            print("### SQLite DB connected ✅", rows)
        elif backend == "postgresql":
            ver = conn.execute(text("select version()")).scalar_one()
            who = conn.execute(text("select current_user")).scalar_one()
            dbn = conn.execute(text("select current_database()")).scalar_one()
            print("### PostgreSQL connected ✅")
            print("    version:", ver)
            print("    user:", who)
            print("    database:", dbn)
        else:
            print(f"### DB backend detected:", backend)
except Exception as e:
    print("### ⚠️ DB connection failed:", e)

# ✅ 4) 라우터 등록
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.postings import router as postings_router
from app.routers.favorites import router as favorites_router
from app.routers.predict import router as predict_router
from app.routers.image import router as image_router

routers = [
    health_router,
    auth_router,
    users_router,
    postings_router,
    favorites_router,
    predict_router,
    image_router,
]

for r in routers:
    app.include_router(r)

# ✅ 5) 등록된 라우트 확인 로그
print("### ROUTES (method, path)")
for r in app.routes:
    try:
        print("   ", getattr(r, "methods", None), getattr(r, "path", None))
    except Exception:
        pass


# ✅ 6) Swagger UI 수정 (Bearer 토큰만 입력하도록 커스텀)
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    """
    Swagger Authorize 팝업을 BearerAuth 한 칸만 뜨게 수정
    """
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version="1.0.0",
        description="Pre-loved API",
        routes=app.routes,
    )

    # 1️⃣ securitySchemes 구성
    comps = schema.setdefault("components", {})
    schemes = comps.setdefault("securitySchemes", {})

    # 2️⃣ 기존 oauth2 스키마 제거 (OAuth2PasswordBearer 제거)
    for key in list(schemes.keys()):
        if schemes[key].get("type") == "oauth2":
            schemes.pop(key, None)

    # 3️⃣ BearerAuth 추가
    schemes["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }

    # 4️⃣ 모든 경로에 BearerAuth 보안 스키마 적용
    for path_item in schema.get("paths", {}).values():
        for op in list(path_item.values()):
            if isinstance(op, dict):
                op["security"] = [{"BearerAuth": []}]

    # 5️⃣ 전역 security 설정
    schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi
