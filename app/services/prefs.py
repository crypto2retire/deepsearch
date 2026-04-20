"""
Global LLM preferences — cached at app startup.
"""
import os

_cached_prefs: dict | None = None

_DEFAULTS = {
    "provider_type": os.environ.get("PROVIDER_TYPE", "openrouter"),
    "provider_api_key": os.environ.get("PROVIDER_API_KEY", ""),
    "planner_model": os.environ.get(
        "PLANNER_MODEL", "meta-llama/llama-3.1-8b-instruct"
    ),
    "researcher_model_1": os.environ.get(
        "RESEARCHER_MODEL_1", "meta-llama/llama-3.3-70b-instruct"
    ),
    "researcher_model_2": os.environ.get(
        "RESEARCHER_MODEL_2", "anthropic/claude-3.5-sonnet"
    ),
    "synthesizer_model": os.environ.get(
        "SYNTHESIZER_MODEL", "meta-llama/llama-3.3-70b-instruct"
    ),
}


def get_global_llm_prefs() -> dict:
    if _cached_prefs is not None:
        return _cached_prefs.copy()
    return _DEFAULTS.copy()


def set_global_prefs(prefs: dict) -> None:
    global _cached_prefs
    _cached_prefs = prefs.copy()


def get_tavily_api_key() -> str:
    from app.config import get_settings
    settings = get_settings()
    return os.environ.get("TAVILY_API_KEY", settings.TAVILY_API_KEY or "")
