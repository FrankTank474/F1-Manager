from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "F1 Manager 2026"
    DEBUG: bool = False
    SECRET_KEY: str = "dev-secret-key-change-in-production"

    # JWT - Keep secret stable to preserve sessions across server restarts
    JWT_SECRET_KEY: str = "jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours (was 15 min)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days (was 7)

    # Datastore
    DATASTORE_TYPE: str = "local"  # "local" or "postgres"
    LOCAL_DATA_DIR: str = "./data"
    DATABASE_URL: str = ""

    # CORS
    CORS_ORIGINS: str = '["http://localhost:8000", "http://127.0.0.1:8000"]'

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 5
    RATE_LIMIT_WINDOW: int = 900  # 15 minutes

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def cors_origins_list(self) -> List[str]:
        import json
        if isinstance(self.CORS_ORIGINS, str):
            return json.loads(self.CORS_ORIGINS)
        return self.CORS_ORIGINS

    @property
    def data_path(self) -> Path:
        return Path(self.LOCAL_DATA_DIR)


settings = Settings()
