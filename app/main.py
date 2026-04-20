import os

from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from sqlalchemy import select, text
import json

from app.config import get_settings
from app.database import _get_engine, Base, get_db
from app.api.routes import research, settings as settings_router, health
from app.models.research import ResearchSession, SessionStatus, GlobalSetting
from app.services.prefs import get_global_llm_prefs, set_global_prefs, _DEFAULTS

settings = get_settings()
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()

    if s.DATABASE_URL:
        engine = _get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        try:
            async for db in get_db():
                # Add new columns if they don't exist yet (live migration)
                for col, typ in [
                    ("researcher_model_1", "VARCHAR(200)"),
                    ("researcher_model_2", "VARCHAR(200)"),
                ]:
                    try:
                        await db.execute(
                            text(f"ALTER TABLE global_settings ADD COLUMN IF NOT EXISTS {col} {typ}")
                        )
                    except Exception:
                        pass

                result = await db.execute(select(GlobalSetting).limit(1))
                row = result.scalar_one_or_none()
                if row:
                    set_global_prefs({
                        "provider_type": row.provider_type,
                        "provider_api_key": row.provider_api_key,
                        "planner_model": row.planner_model,
                        "researcher_model_1": row.researcher_model_1 or _DEFAULTS["researcher_model_1"],
                        "researcher_model_2": row.researcher_model_2 or _DEFAULTS["researcher_model_2"],
                        "synthesizer_model": row.synthesizer_model,
                    })
                else:
                    set_global_prefs(_DEFAULTS.copy())
                break
        except Exception:
            set_global_prefs(_DEFAULTS.copy())

        yield
        await engine.dispose()
    else:
        set_global_prefs(_DEFAULTS.copy())
        yield


app = FastAPI(
    title="DeepSearch API",
    description="Multi-agent deep research pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

templates = Jinja2Templates(directory="app/templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(research.router)
app.include_router(settings_router.router)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/dashboard", status_code=307)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    async for db in get_db():
        result = await db.execute(
            select(ResearchSession)
            .order_by(ResearchSession.created_at.desc())
            .limit(50)
        )
        sessions = result.scalars().all()
        history = [
            {"id": s.id, "query": s.query, "status": s.status.value}
            for s in sessions
        ]
        return templates.TemplateResponse(
            request,
            "research/dashboard.html",
            {"history": history, "result": None},
        )


@app.post("/research/start")
async def start_research(query: str = Form(...)) -> JSONResponse:
    prefs = get_global_llm_prefs()
    if not prefs["provider_api_key"]:
        raise HTTPException(
            status_code=400,
            detail="Set your API key in Settings first.",
        )
    async for db in get_db():
        session = ResearchSession(user_id=None, query=query, status=SessionStatus.PENDING)
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return JSONResponse(
            content={
                "id": session.id,
                "query": session.query,
                "status": session.status.value,
            },
            media_type="application/json",
        )


@app.get("/research/{job_id}", response_class=HTMLResponse)
async def view_research(request: Request, job_id: str):
    async for db in get_db():
        result = await db.execute(
            select(ResearchSession).where(ResearchSession.id == job_id)
        )
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
            {"id": s.id, "query": s.query, "status": s.status.value}
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

        return templates.TemplateResponse(
            request,
            "research/dashboard.html",
            {
                "history": history,
                "result": {
                    "id": session.id,
                    "query": session.query,
                    "status": session.status.value,
                    "answer_markdown": answer_data or "",
                    "follow_up_questions": follow_ups,
                },
            },
        )
