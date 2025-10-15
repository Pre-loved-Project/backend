# app/core/config.py

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseSettings
    SettingsConfigDict = None

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./app.db"

    JWT_SECRET: str = "change-this-secret"
    JWT_ACCESS_SECRET: str = "change-this-secret"
    JWT_REFRESH_SECRET: str = "change-this-refresh-secret"
    JWT_ALG: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    EMAIL_TOKEN_EXPIRE_MINUTES: int = 30

    # AWS는 안 쓰면 빈값
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET_NAME: str = ""

    # ✅ 오타 수정 + 기본값 부여
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_CONTAINER_NAME: str = ""

    if SettingsConfigDict:
        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    else:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"

settings = Settings()
