"""
Global LLM preferences — stored in the GlobalSetting DB table.
Env vars are only used as fallback if no DB row exists yet.
"""
import os
from app.config import get_settings

settings = get_settings()

# Env-var defaults (used only when DB has no row yet)
_DEFAULTS = {
    "provider_type": os.environ.get("PROVIDER_TYPE", "openrouter"),
    "provider_api_key": os.environ.get("PROVIDER_API_KEY", ""),
    "planner_model": os.environ.get("PLANNER_MODEL", "openrouter/meta-llama/llama-3.1-8b-instruct"),
    "researcher_model": os.environ.get("RESEARCHER_MODEL", "openrouter/meta-llama/llama-3.3-70b-instruct"),
    "synthesizer_model": os.environ.get("SYNTHESIZER_MODEL", "openrouter/meta-llama/llama-3.3-70b-instruct"),
}


def get_global_llm_prefs() -> dict:
    from app.database import get_db
    from app.models.research import GlobalSetting
    from sqlalchemy import select

    try:
        async for db in get_db():
            result = await db.execute(select(GlobalSetting).limit(1))
            row = result.scalar_one_or_none()
            if row:
                return {
                    "provider_type": row.provider_type,
                    "provider_api_key": row.provider_api_key,
                    "planner_model": row.planner_model,
                    "researcher_model": row.researcher_model,
                    "synthesizer_model": row.synthesizer_model,
                }
    except Exception:
        pass  # DB not ready yet, fall through to env defaults

    return _DEFAULTS.copy()


def get_tavily_api_key() -> str:
    return os.environ.get("TAVILY_API_KEY", settings.TAVILY_API_KEY or "")
