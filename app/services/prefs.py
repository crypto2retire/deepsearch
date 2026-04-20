"""
Global LLM preferences — stored in Railway environment variables.
No per-user auth required.
"""
import os
from app.config import get_settings

settings = get_settings()


def get_global_llm_prefs() -> dict:
    return {
        "provider_type": os.environ.get("PROVIDER_TYPE", "openrouter"),
        "provider_api_key": os.environ.get("PROVIDER_API_KEY", ""),
        "planner_model": os.environ.get("PLANNER_MODEL", "openrouter/meta-llama/llama-3.1-8b-instruct"),
        "researcher_model": os.environ.get("RESEARCHER_MODEL", "openrouter/meta-llama/llama-3.3-70b-instruct"),
        "synthesizer_model": os.environ.get("SYNTHESIZER_MODEL", "openrouter/meta-llama/llama-3.3-70b-instruct"),
    }


def get_tavily_api_key() -> str:
    return os.environ.get("TAVILY_API_KEY", settings.TAVILY_API_KEY or "")