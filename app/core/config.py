# app/core/config.py
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseSettings
    SettingsConfigDict = None

class Settings(BaseSettings):
    DATABASE_URL: str

    # legacy: JWT_SECRET 유지(=access와 동일 값). 앞으로는 JWT_ACCESS_SECRET 사용
    JWT_SECRET: str = "change-this-secret"
    JWT_ACCESS_SECRET: str = "change-this-secret"
    JWT_REFRESH_SECRET: str = "change-this-refresh-secret"
    JWT_ALG: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    EMAIL_TOKEN_EXPIRE_MINUTES: int = 30

    if SettingsConfigDict:
        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    else:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"

settings = Settings()
