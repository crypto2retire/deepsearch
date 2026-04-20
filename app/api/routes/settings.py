"""
Global LLM settings — stored in DB, cached in memory via prefs service.
"""
import os
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.database import get_db
from app.models.research import GlobalSetting
from app.services.prefs import get_global_llm_prefs, set_global_prefs, _DEFAULTS
from sqlalchemy import select

router = APIRouter(prefix="", tags=["settings"])
templates = Jinja2Templates(directory="app/templates")

AVAILABLE_PROVIDERS = [
    {"id": "openrouter", "label": "OpenRouter"},
    {"id": "openai", "label": "OpenAI"},
    {"id": "anthropic", "label": "Anthropic"},
    {"id": "google", "label": "Google AI"},
    {"id": "minimax", "label": "MiniMax"},
    {"id": "z.ai", "label": "Z.ai"},
]

AVAILABLE_MODELS = {
    "openrouter": [
        "openrouter/meta-llama/llama-3.1-8b-instruct",
        "openrouter/meta-llama/llama-3.3-70b-instruct",
        "openrouter/meta-llama/llama-4-70b-instruct",
        "openrouter/mistralai/mistral-7b-instruct",
        "openrouter/mistralai/mixtral-8x7b-instruct",
        "openrouter/anthropic/claude-3.5-haiku",
        "openrouter/anthropic/claude-3.5-sonnet",
        "openrouter/anthropic/claude-3.7-sonnet",
        "openrouter/google/gemini-pro-1.5",
        "openrouter/openai/gpt-4o-mini",
        "openrouter/openai/gpt-4o",
        "openrouter/deepseek/deepseek-chat",
        "openrouter/qwen/qwen-2.5-72b-instruct",
        "custom",
    ],
    "openai": [
        "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "custom",
    ],
    "anthropic": [
        "claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022",
        "claude-3-7-sonnet-20241022", "claude-opus-4-20250514", "custom",
    ],
    "google": [
        "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash",
        "gemini-exp-1206", "custom",
    ],
    "minimax": ["MiniMax-Text-01", "abab6.5s-chat", "custom"],
    "z.ai": ["custom"],
}


def _load_settings() -> dict:
    """Read current settings from the cached prefs service."""
    return get_global_llm_prefs()


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    prefs = _load_settings()
    provider = prefs["provider_type"]
    models = AVAILABLE_MODELS.get(provider, [])

    def model_selected(current: str, model_id: str) -> str:
        return "selected" if current == model_id else ""

    return templates.TemplateResponse(
        "research/settings.html",
        {
            "prefs": prefs,
            "providers": AVAILABLE_PROVIDERS,
            "provider_models": AVAILABLE_MODELS,
            "model_selected": model_selected,
            "provider_selected": provider,
        },
    )


@router.post("/settings")
async def settings_post(
    request: Request,
    provider_type: str = Form(...),
    provider_api_key: str = Form(...),
    planner_model: str = Form(...),
    planner_custom: str = Form(""),
    researcher_model: str = Form(...),
    researcher_custom: str = Form(""),
    synthesizer_model: str = Form(...),
    synthesizer_custom: str = Form(""),
):
    # Resolve "custom" selections
    planner = planner_custom if planner_model == "custom" else planner_model
    researcher = researcher_custom if researcher_model == "custom" else researcher_model
    synthesizer = synthesizer_custom if synthesizer_model == "custom" else synthesizer_model

    async for db in get_db():
        result = await db.execute(select(GlobalSetting).limit(1))
        row = result.scalar_one_or_none()
        if row:
            row.provider_type = provider_type
            row.provider_api_key = provider_api_key
            row.planner_model = planner
            row.researcher_model = researcher
            row.synthesizer_model = synthesizer
        else:
            row = GlobalSetting(
                provider_type=provider_type,
                provider_api_key=provider_api_key,
                planner_model=planner,
                researcher_model=researcher,
                synthesizer_model=synthesizer,
            )
            db.add(row)
        await db.commit()

    prefs = {
        "provider_type": provider_type,
        "provider_api_key": provider_api_key,
        "planner_model": planner,
        "researcher_model": researcher,
        "synthesizer_model": synthesizer,
    }
    # Update the in-memory cache so next request doesn't need DB
    set_global_prefs(prefs)

    return templates.TemplateResponse(
        "research/settings.html",
        {
            "prefs": prefs,
            "providers": AVAILABLE_PROVIDERS,
            "provider_models": AVAILABLE_MODELS,
            "model_selected": lambda cur, mid: "selected" if cur == mid else "",
            "provider_selected": provider_type,
            "success": "Settings saved! They will be used for your next research query.",
        },
    )