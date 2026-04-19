from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = ""
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
    def DATABASE_URL_SYNC(self) -> str:
        """Derive sync URL from async URL by stripping the +asyncpg driver prefix."""
        if not self.DATABASE_URL:
            return ""
        return self.DATABASE_URL.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
