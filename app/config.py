from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = ""
    DATABASE_URL_SYNC: str = ""
    JWT_SECRET: str = ""
    TAVILY_API_KEY: str = ""
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "validate_default": False,
    }

    @property
    def sync_db_url(self) -> str:
        return self.DATABASE_URL_SYNC or self.DATABASE_URL.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
