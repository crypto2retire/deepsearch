"""
Global LLM settings — stored in DB, cached in memory via prefs service.
"""
import os
import logging
import httpx
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.database import get_db
from app.models.research import GlobalSetting
from app.services.prefs import get_global_llm_prefs, set_global_prefs, _DEFAULTS
from sqlalchemy import select

logger = logging.getLogger("deepsearch.settings")

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
        {"id": "openai/gpt-4o", "name": "GPT-4o"},
        {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini (cheap/fast)"},
        {"id": "openai/gpt-4-turbo", "name": "GPT-4 Turbo"},
        {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet"},
        {"id": "anthropic/claude-3.5-haiku", "name": "Claude 3.5 Haiku (cheap/fast)"},
        {"id": "anthropic/claude-3.7-sonnet", "name": "Claude 3.7 Sonnet"},
        {"id": "google/gemini-pro-1.5", "name": "Gemini 1.5 Pro"},
        {"id": "google/gemini-flash-1.5", "name": "Gemini 1.5 Flash (cheap/fast)"},
        {"id": "meta-llama/llama-3.1-8b-instruct", "name": "Llama 3.1 8B (cheap/fast)"},
        {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B"},
        {"id": "meta-llama/llama-4-maverick-17b-instruct", "name": "Llama 4 Maverick 17B"},
        {"id": "deepseek/deepseek-chat", "name": "DeepSeek V3"},
        {"id": "deepseek/deepseek-r1", "name": "DeepSeek R1 (reasoning)"},
        {"id": "qwen/qwen-2.5-72b-instruct", "name": "Qwen 2.5 72B"},
        {"id": "mistralai/mistral-7b-instruct", "name": "Mistral 7B (cheap/fast)"},
        {"id": "mistralai/mixtral-8x7b-instruct", "name": "Mixtral 8x7B"},
    ],
    "openai": [
        {"id": "gpt-4o", "name": "GPT-4o"},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini (cheap/fast)"},
        {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"},
        {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo (cheap/fast)"},
    ],
    "anthropic": [
        {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"},
        {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku (cheap/fast)"},
        {"id": "claude-3-7-sonnet-20250219", "name": "Claude 3.7 Sonnet"},
        {"id": "claude-opus-4-20250514", "name": "Claude Opus 4 (powerful)"},
    ],
    "google": [
        {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
        {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash (cheap/fast)"},
        {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
        {"id": "gemini-2.5-flash-preview-05-20", "name": "Gemini 2.5 Flash Preview"},
    ],
    "minimax": [
        {"id": "MiniMax-Text-01", "name": "MiniMax Text 01"},
        {"id": "abab6.5s-chat", "name": "ABAB 6.5S Chat"},
    ],
    "z.ai": [
        {"id": "glm-4-plus", "name": "GLM-4 Plus"},
        {"id": "glm-4-flash", "name": "GLM-4 Flash (cheap/fast)"},
        {"id": "glm-4-air", "name": "GLM-4 Air"},
        {"id": "glm-4-long", "name": "GLM-4 Long (128K context)"},
        {"id": "glm-3-turbo", "name": "GLM-3 Turbo (cheap/fast)"},
    ],
}


@router.get("/api/models/{provider}")
async def fetch_models(provider: str):
    if provider == "openrouter":
        prefs = get_global_llm_prefs()
        api_key = prefs.get("provider_api_key", "")
        if not api_key:
            return JSONResponse(status_code=400, content={"error": "No OpenRouter API key configured"})
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()
                models = []
                for m in data.get("data", []):
                    mid = m.get("id", "")
                    name = m.get("name", mid)
                    pricing = m.get("pricing", {})
                    prompt_price = float(pricing.get("prompt", "1") or "1")
                    tag = ""
                    if prompt_price == 0:
                        tag = " (FREE)"
                    elif prompt_price < 0.0001:
                        tag = " (cheap)"
                    models.append({"id": mid, "name": name + tag})
                models.sort(key=lambda x: x["name"].lower())
                return {"models": models}
        except Exception as e:
            logger.error(f"Failed to fetch OpenRouter models: {e}")
            return JSONResponse(status_code=502, content={"error": str(e)})
    if provider == "z.ai":
        prefs = get_global_llm_prefs()
        api_key = prefs.get("provider_api_key", "")
        if not api_key:
            return JSONResponse(status_code=400, content={"error": "No Z.ai API key configured"})
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://open.bigmodel.cn/api/paas/v4/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    models = []
                    for m in data.get("data", []):
                        mid = m.get("id", "")
                        models.append({"id": mid, "name": mid})
                    return {"models": models}
        except Exception:
            pass
        return {"models": AVAILABLE_MODELS.get("z.ai", [])}
    models = AVAILABLE_MODELS.get(provider, [])
    return {"models": models}


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    prefs = get_global_llm_prefs()
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