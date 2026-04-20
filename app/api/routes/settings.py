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
        "meta-llama/llama-3.1-8b-instruct",
        "meta-llama/llama-3.3-70b-instruct",
        "meta-llama/llama-4-maverick-17b-instruct",
        "mistralai/mistral-7b-instruct",
        "mistralai/mixtral-8x7b-instruct",
        "anthropic/claude-3.5-haiku",
        "anthropic/claude-3.5-sonnet",
        "anthropic/claude-3.7-sonnet",
        "google/gemini-pro-1.5",
        "openai/gpt-4o-mini",
        "openai/gpt-4o",
        "deepseek/deepseek-chat",
        "qwen/qwen-2.5-72b-instruct",
        "custom",
    ],
    "openai": [
        "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "custom",
    ],
    "anthropic": [
        "claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022",
        "claude-3-7-sonnet-20250219", "claude-opus-4-20250514", "custom",
    ],
    "google": [
        "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash",
        "gemini-2.5-flash-preview-05-20", "custom",
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

    return templates.TemplateResponse(
        request,
        "research/settings.html",
        {
            "prefs": prefs,
            "providers": AVAILABLE_PROVIDERS,
            "provider_models": AVAILABLE_MODELS,
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
    planner_provider: str = Form(""),
    planner_api_key: str = Form(""),
    researcher_model: str = Form(...),
    researcher_custom: str = Form(""),
    researcher_provider_1: str = Form(""),
    researcher_api_key_1: str = Form(""),
    researcher_model_2_raw: str = Form(...),
    researcher_model_2_custom: str = Form(""),
    researcher_provider_2: str = Form(""),
    researcher_api_key_2: str = Form(""),
    synthesizer_model: str = Form(...),
    synthesizer_custom: str = Form(""),
    synthesizer_provider: str = Form(""),
    synthesizer_api_key: str = Form(""),
):
    planner = planner_custom if planner_model == "custom" else planner_model
    researcher_1 = researcher_custom if researcher_model == "custom" else researcher_model
    researcher_2 = researcher_model_2_raw if researcher_model_2_raw != "custom" else researcher_model_2_custom
    synthesizer = synthesizer_custom if synthesizer_model == "custom" else synthesizer_model

    try:
        async for db in get_db():
            result = await db.execute(select(GlobalSetting).limit(1))
            row = result.scalar_one_or_none()
            if row:
                row.provider_type = provider_type
                row.provider_api_key = provider_api_key
                row.planner_model = planner
                row.planner_provider = planner_provider or provider_type
                row.planner_api_key = planner_api_key
                row.researcher_model_1 = researcher_1
                row.researcher_provider_1 = researcher_provider_1 or provider_type
                row.researcher_api_key_1 = researcher_api_key_1
                row.researcher_model_2 = researcher_2
                row.researcher_provider_2 = researcher_provider_2 or provider_type
                row.researcher_api_key_2 = researcher_api_key_2
                row.synthesizer_model = synthesizer
                row.synthesizer_provider = synthesizer_provider or provider_type
                row.synthesizer_api_key = synthesizer_api_key
            else:
                row = GlobalSetting(
                    provider_type=provider_type,
                    provider_api_key=provider_api_key,
                    planner_model=planner,
                    planner_provider=planner_provider or provider_type,
                    planner_api_key=planner_api_key,
                    researcher_model_1=researcher_1,
                    researcher_provider_1=researcher_provider_1 or provider_type,
                    researcher_api_key_1=researcher_api_key_1,
                    researcher_model_2=researcher_2,
                    researcher_provider_2=researcher_provider_2 or provider_type,
                    researcher_api_key_2=researcher_api_key_2,
                    synthesizer_model=synthesizer,
                    synthesizer_provider=synthesizer_provider or provider_type,
                    synthesizer_api_key=synthesizer_api_key,
                )
                db.add(row)
            await db.commit()
    except Exception:
        pass

    prefs = {
        "provider_type": provider_type,
        "provider_api_key": provider_api_key,
        "planner_model": planner,
        "planner_provider": planner_provider or provider_type,
        "planner_api_key": planner_api_key,
        "researcher_model_1": researcher_1,
        "researcher_provider_1": researcher_provider_1 or provider_type,
        "researcher_api_key_1": researcher_api_key_1,
        "researcher_model_2": researcher_2,
        "researcher_provider_2": researcher_provider_2 or provider_type,
        "researcher_api_key_2": researcher_api_key_2,
        "synthesizer_model": synthesizer,
        "synthesizer_provider": synthesizer_provider or provider_type,
        "synthesizer_api_key": synthesizer_api_key,
    }
    set_global_prefs(prefs)

    return templates.TemplateResponse(
        request,
        "research/settings.html",
        {
            "prefs": prefs,
            "providers": AVAILABLE_PROVIDERS,
            "provider_models": AVAILABLE_MODELS,
            "provider_selected": provider_type,
            "success": "Settings saved! They will be used for your next research query.",
        },
    )