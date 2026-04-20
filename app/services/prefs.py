"""
Global LLM preferences — cached at app startup.
Only reads from DB once at startup; kept in sync via set_global_prefs().
"""
import os

# Module-level cache — populated once by set_global_prefs() in lifespan
_cached_prefs: dict | None = None

_DEFAULTS = {
    "provider_type": os.environ.get("PROVIDER_TYPE", "openrouter"),
    "provider_api_key": os.environ.get("PROVIDER_API_KEY", ""),
    "planner_model": os.environ.get(
        "PLANNER_MODEL", "openrouter/meta-llama/llama-3.1-8b-instruct"
    ),
    "researcher_model": os.environ.get(
        "RESEARCHER_MODEL", "openrouter/meta-llama/llama-3.3-70b-instruct"
    ),
    "synthesizer_model": os.environ.get(
        "SYNTHESIZER_MODEL", "openrouter/meta-llama/llama-3.3-70b-instruct"
    ),
}


def get_global_llm_prefs() -> dict:
    """Return cached prefs. Falls back to env defaults if cache is cold."""
    if _cached_prefs is not None:
        return _cached_prefs.copy()
    return _DEFAULTS.copy()


def set_global_prefs(prefs: dict) -> None:
    """Replace the in-memory cache. Called once at startup and after settings saves."""
    global _cached_prefs
    _cached_prefs = prefs.copy()


def get_tavily_api_key() -> str:
    from app.config import get_settings
    settings = get_settings()
    return os.environ.get("TAVILY_API_KEY", settings.TAVILY_API_KEY or "")
