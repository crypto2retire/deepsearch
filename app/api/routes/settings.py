import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="", tags=["settings"])

templates = Jinja2Templates(directory="app/templates")


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse(
        "research/settings.html",
        {
            "prefs": {
                "provider_type": os.environ.get("PROVIDER_TYPE", "openrouter"),
                "provider_api_key": os.environ.get("PROVIDER_API_KEY", ""),
                "planner_model": os.environ.get("PLANNER_MODEL", "openrouter/meta-llama/llama-3.1-8b-instruct"),
                "researcher_model": os.environ.get("RESEARCHER_MODEL", "openrouter/meta-llama/llama-3.3-70b-instruct"),
                "synthesizer_model": os.environ.get("SYNTHESIZER_MODEL", "openrouter/meta-llama/llama-3.3-70b-instruct"),
            },
        },
    )


@router.post("/settings")
async def settings_post(request: Request):
    # Settings are stored in Railway environment variables.
    # This page is informational — configure keys via Railway dashboard.
    return templates.TemplateResponse(
        "research/settings.html",
        {
            "prefs": {
                "provider_type": os.environ.get("PROVIDER_TYPE", "openrouter"),
                "provider_api_key": os.environ.get("PROVIDER_API_KEY", ""),
                "planner_model": os.environ.get("PLANNER_MODEL", "openrouter/meta-llama/llama-3.1-8b-instruct"),
                "researcher_model": os.environ.get("RESEARCHER_MODEL", "openrouter/meta-llama/llama-3.3-70b-instruct"),
                "synthesizer_model": os.environ.get("SYNTHESIZER_MODEL", "openrouter/meta-llama/llama-3.3-70b-instruct"),
            },
            "success": "Settings are read from Railway environment variables. Update them in your Railway project settings.",
        },
    )