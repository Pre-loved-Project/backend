# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.db import Base, engine
from app.models.user import User
from app.models.posting import Posting
from app.models.favorite import Favorite
from app.models.consent import UserConsent
from app.models.email_verification import EmailVerification
from app.routers import users, auth, postings, favorites, predict

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pre-loved API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(postings.router)
app.include_router(favorites.router)
app.include_router(predict.router)

@app.get("/health")
def health():
    return {"status": "ok"}
