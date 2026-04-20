"""
Global LLM preferences — cached at app startup, updated via settings route.
"""
import os
from app.config import get_settings

settings = get_settings()

# Cached at startup by app.lifespan, updated by settings route
_cached_prefs: dict | None = None

_DEFAULTS = {
    "provider_type": os.environ.get("PROVIDER_TYPE", "openrouter"),
    "provider_api_key": os.environ.get("PROVIDER_API_KEY", ""),
    "planner_model": os.environ.get("PLANNER_MODEL", "openrouter/meta-llama/llama-3.1-8b-instruct"),
    "researcher_model": os.environ.get("RESEARCHER_MODEL", "openrouter/meta-llama/llama-3.3-70b-instruct"),
    "synthesizer_model": os.environ.get("SYNTHESIZER_MODEL", "openrouter/meta-llama/llama-3.3-70b-instruct"),
}


def get_global_llm_prefs() -> dict:
    """Return cached prefs (loaded once at startup). Falls back to env defaults."""
    if _cached_prefs is not None:
        return _cached_prefs.copy()
    return _DEFAULTS.copy()


def set_global_prefs(prefs: dict) -> None:
    """Called by settings route after a save to keep cache in sync."""
    global _cached_prefs
    _cached_prefs = prefs.copy()


def load_prefs_from_db() -> dict:
    """Called once by lifespan. Returns DB row or env defaults."""
    from app.database import get_db
    from app.models.research import GlobalSetting
    from sqlalchemy import select

    try:
        import asyncio
        # Run the async DB call in a new event loop (only during startup)
        async def _fetch():
            async for db in get_db():
                result = await db.execute(select(GlobalSetting).limit(1))
                return result.scalar_one_or_none()

        loop = asyncio.new_event_loop()
        try:
            row = loop.run_until_complete(_fetch())
        finally:
            loop.close()

        if row:
            return {
                "provider_type": row.provider_type,
                "provider_api_key": row.provider_api_key,
                "planner_model": row.planner_model,
                "researcher_model": row.researcher_model,
                "synthesizer_model": row.synthesizer_model,
            }
    except Exception:
        pass

    return _DEFAULTS.copy()


def get_tavily_api_key() -> str:
    return os.environ.get("TAVILY_API_KEY", settings.TAVILY_API_KEY or "")