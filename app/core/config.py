# app/core/config.py
try:
    # Pydantic v2
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    # (혹시 v1로 돌릴 때를 위한 안전장치)
    from pydantic import BaseSettings
    SettingsConfigDict = None

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./app.db"

    JWT_SECRET: str = "change-this-secret"
    JWT_REFRESH_SECRET: str = "change-this-refresh-secret"
    JWT_ALG: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    EMAIL_TOKEN_EXPIRE_MINUTES: int = 30

    # v2
    if SettingsConfigDict:
        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    else:
        # v1 fallback
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"

settings = Settings()
