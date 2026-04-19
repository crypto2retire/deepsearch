from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import TemplateResponse
from contextlib import asynccontextmanager
from sqlalchemy import select
import json

from app.config import get_settings
from app.database import _get_engine, Base, get_db
from app.api.routes import auth, research, settings as settings_router, health
from app.services.auth import create_access_token, verify_password, hash_password
from app.models.user import User
from app.models.research import ResearchSession, SessionStatus
from app.services.auth import decode_token

settings = get_settings()
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    if s.DATABASE_URL:
        engine = _get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield
        await engine.dispose()
    else:
        yield


app = FastAPI(
    title="DeepSearch API",
    description="Multi-agent deep research pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(research.router)
app.include_router(settings_router.router)
app.include_router(health.router)


# ─── HTML Pages (no auth required for now) ─────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/dashboard", status_code=307)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        try:
            decode_token(token)
        except Exception:
            return RedirectResponse(url="/", status_code=307)

    async for db in get_db():
        result = await db.execute(
            select(ResearchSession)
            .order_by(ResearchSession.created_at.desc())
            .limit(20)
        )
        sessions = result.scalars().all()
        history = [
            {
                "id": s.id,
                "query": s.query,
                "status": s.status.value,
            }
            for s in sessions
        ]
        return TemplateResponse("research/dashboard.html", {
            "request": request,
            "history": history,
            "result": None,
        })


@app.post("/research/start")
async def start_research(request: Request, query: str = Form(...)):
    async for db in get_db():
        session = ResearchSession(query=query, status=SessionStatus.PENDING)
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return {
            "id": session.id,
            "query": session.query,
            "status": session.status.value,
        }


@app.get("/research/{job_id}", response_class=HTMLResponse)
async def view_research(request: Request, job_id: str):
    async for db in get_db():
        result = await db.execute(select(ResearchSession).where(ResearchSession.id == job_id))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Research job not found")

        hist_result = await db.execute(
            select(ResearchSession)
            .order_by(ResearchSession.created_at.desc())
            .limit(20)
        )
        sessions = hist_result.scalars().all()
        history = [
            {
                "id": s.id,
                "query": s.query,
                "status": s.status.value,
            }
            for s in sessions
        ]

        answer_data = None
        follow_ups = []
        if session.answer:
            answer_data = session.answer.answer_markdown
            try:
                follow_ups = json.loads(session.answer.follow_up_questions or "[]")
            except Exception:
                pass

        return TemplateResponse("research/dashboard.html", {
            "request": request,
            "history": history,
            "result": {
                "id": session.id,
                "query": session.query,
                "status": session.status.value,
                "answer_markdown": answer_data or "",
                "follow_up_questions": follow_ups,
            },
        })


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return TemplateResponse("research/settings.html", {
        "request": request,
        "prefs": {
            "provider_type": "openrouter",
            "provider_api_key": "",
            "planner_model": "openrouter/meta-llama/llama-3.1-8b-instruct",
            "researcher_model": "openrouter/meta-llama/llama-3.3-70b-instruct",
            "synthesizer_model": "openrouter/meta-llama/llama-3.3-70b-instruct",
        },
    })


@app.post("/settings", response_class=HTMLResponse)
async def settings_post(
    request: Request,
    provider_type: str = Form(...),
    provider_api_key: str = Form(...),
    planner_model: str = Form(...),
    researcher_model: str = Form(...),
    synthesizer_model: str = Form(...),
):
    return TemplateResponse("research/settings.html", {
        "request": request,
        "prefs": {
            "provider_type": provider_type,
            "provider_api_key": provider_api_key,
            "planner_model": planner_model,
            "researcher_model": researcher_model,
            "synthesizer_model": synthesizer_model,
        },
        "success": "Settings saved!",
    })
