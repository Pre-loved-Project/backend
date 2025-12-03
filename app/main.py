# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.db import Base, engine
from app.core.config import settings
from app.routers import chat_ws, chat_list_ws 

app = FastAPI(title="Pre-loved API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://chalddack.vercel.app",  # ✅ 프론트 배포 주소 추가
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from app.models.user import User
from app.models.posting import Posting, PostingImage
from app.models.favorite import Favorite
from app.models.consent import UserConsent
from app.models.email_verification import EmailVerification
from app.models.chat import ChatRoom, ChatMessage, ChatRead

print("### DB URL =", settings.DATABASE_URL)
print("### tables BEFORE:", list(Base.metadata.tables.keys()))
Base.metadata.create_all(bind=engine)
print("### tables AFTER :", list(Base.metadata.tables.keys()))

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
            print("### DB backend detected:", backend)
except Exception as e:
    print("### ⚠️ DB connection failed:", e)

from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.postings import router as postings_router
from app.routers.favorites import router as favorites_router
from app.routers.predict import router as predict_router
from app.routers.image import router as image_router
from app.routers import chat
from app.routers import chat_rest

routers = [
    health_router,
    auth_router,
    users_router,
    postings_router,
    favorites_router,
    predict_router,
    image_router,
    chat.router,
    chat_rest.router,
    chat_ws.router,
    chat_list_ws.router,
]

for r in routers:
    app.include_router(r)

print("### ROUTES (method, path)")
for r in app.routes:
    try:
        print("   ", getattr(r, "methods", None), getattr(r, "path", None))
    except Exception:
        pass

from fastapi.openapi.utils import get_openapi
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version="1.0.0",
        description="Pre-loved API",
        routes=app.routes,
    )
    comps = schema.setdefault("components", {})
    schemes = comps.setdefault("securitySchemes", {})
    for key in list(schemes.keys()):
        if schemes[key].get("type") == "oauth2":
            schemes.pop(key, None)
    schemes["BearerAuth"] = {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    for path_item in schema.get("paths", {}).values():
        for op in list(path_item.values()):
            if isinstance(op, dict):
                op["security"] = [{"BearerAuth": []}]
    schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi
