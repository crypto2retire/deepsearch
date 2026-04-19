from fastapi import FastAPI, Depends, Form, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from app.config import get_settings
from app.database import _get_engine, _get_session_maker, Base, get_db
from app.api.routes import auth, research, settings as settings_router, health
from app.api.deps import get_current_user
from app.services.auth import create_access_token, verify_password, hash_password
from app.models.user import User
from app.models.research import ResearchSession, SessionStatus
from app.services.auth import decode_token

settings = get_settings()
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.config import get_settings
    s = get_settings()
    if s.DATABASE_URL:
        from app.database import _get_engine, _get_session_maker, Base
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


# ─── HTML Pages ───────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root redirects to dashboard if authenticated, else login."""
    token = request.cookies.get("access_token")
    if token:
        try:
            decode_token(token)
            return RedirectResponse(url="/dashboard", status_code=307)
        except Exception:
            pass
    return RedirectResponse(url="/login", status_code=307)


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    token = request.cookies.get("access_token")
    if token:
        try:
            decode_token(token)
            return RedirectResponse(url="/dashboard", status_code=307)
        except Exception:
            pass
    from fastapi import TemplateResponse
    return TemplateResponse("auth/login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, email: str = Form(...), password: str = Form(...)):
    from fastapi import TemplateResponse
    from app.database import get_db

    async for db in get_db():
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            return TemplateResponse("auth/login.html", {
                "request": request, "error": "Invalid email or password"
            })
        token = create_access_token({"sub": user.id, "email": user.email})
        resp = RedirectResponse(url="/dashboard", status_code=307)
        resp.set_cookie(
            key="access_token", value=token,
            httponly=True, samesite="lax",
            max_age=60 * 60 * 24  # 24h
        )
        return resp


@app.get("/register", response_class=HTMLResponse)
async def register_get(request: Request):
    token = request.cookies.get("access_token")
    if token:
        try:
            decode_token(token)
            return RedirectResponse(url="/dashboard", status_code=307)
        except Exception:
            pass
    from fastapi import TemplateResponse
    return TemplateResponse("auth/register.html", {"request": request})


@app.post("/register", response_class=HTMLResponse)
async def register_post(request: Request, email: str = Form(...), password: str = Form(...)):
    from fastapi import TemplateResponse
    from app.database import get_db

    async for db in get_db():
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()
        if existing:
            return TemplateResponse("auth/register.html", {
                "request": request, "error": "Email already registered"
            })
        user = User(email=email, password_hash=hash_password(password))
        db.add(user)
        await db.commit()
        return TemplateResponse("auth/register.html", {
            "request": request,
            "success": "Account created! You can now sign in."
        })


@app.post("/logout")
async def logout():
    resp = RedirectResponse(url="/login", status_code=307)
    resp.delete_cookie("access_token")
    return resp


async def get_current_user_from_cookie(request: Request) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        token_data = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    async for db in get_db():
        result = await db.execute(select(User).where(User.id == token_data.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    from fastapi import TemplateResponse
    try:
        user = await get_current_user_from_cookie(request)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=307)

    async for db in get_db():
        result = await db.execute(
            select(ResearchSession)
            .where(ResearchSession.user_id == user.id)
            .order_by(ResearchSession.created_at.desc())
            .limit(20)
        )
        sessions = result.scalars().all()
        history = []
        for s in sessions:
            history.append({
                "id": s.id,
                "query": s.query,
                "status": s.status.value,
                "answer_markdown": None,
                "follow_up_questions": None,
            })
        return TemplateResponse("research/dashboard.html", {
            "request": request,
            "current_email": user.email,
            "history": history,
            "result": None,
        })


@app.post("/research/start")
async def start_research(request: Request, query: str = Form(...)):
    try:
        user = await get_current_user_from_cookie(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async for db in get_db():
        session = ResearchSession(user_id=user.id, query=query, status=SessionStatus.PENDING)
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
    from fastapi import TemplateResponse
    try:
        user = await get_current_user_from_cookie(request)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=307)

    async for db in get_db():
        result = await db.execute(select(ResearchSession).where(ResearchSession.id == job_id))
        session = result.scalar_one_or_none()
        if not session or session.user_id != user.id:
            raise HTTPException(status_code=404, detail="Research job not found")

        # Get history
        hist_result = await db.execute(
            select(ResearchSession)
            .where(ResearchSession.user_id == user.id)
            .order_by(ResearchSession.created_at.desc())
            .limit(20)
        )
        sessions = hist_result.scalars().all()
        history = []
        for s in sessions:
            history.append({
                "id": s.id,
                "query": s.query,
                "status": s.status.value,
                "answer_markdown": None,
                "follow_up_questions": None,
            })

        answer_data = None
        follow_ups = None
        if session.answer:
            answer_data = session.answer.answer_markdown
            try:
                follow_ups = json.loads(session.answer.follow_up_questions or "[]")
            except Exception:
                follow_ups = []

        return TemplateResponse("research/dashboard.html", {
            "request": request,
            "current_email": user.email,
            "history": history,
            "result": {
                "id": session.id,
                "query": session.query,
                "status": session.status.value,
                "answer_markdown": answer_data or "",
                "follow_up_questions": follow_ups or [],
            },
        })


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    from fastapi import TemplateResponse
    try:
        user = await get_current_user_from_cookie(request)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=307)

    async for db in get_db():
        from app.models.research import LLMPreference
        result = await db.execute(select(LLMPreference).where(LLMPreference.user_id == user.id))
        prefs = result.scalar_one_or_none()
        if prefs:
            prefs_dict = {
                "provider_type": prefs.provider_type,
                "provider_api_key": prefs.provider_api_key,
                "planner_model": prefs.planner_model,
                "researcher_model": prefs.researcher_model,
                "synthesizer_model": prefs.synthesizer_model,
            }
        else:
            prefs_dict = {
                "provider_type": "openrouter",
                "provider_api_key": "",
                "planner_model": "openrouter/meta-llama/llama-3.1-8b-instruct",
                "researcher_model": "openrouter/meta-llama/llama-3.3-70b-instruct",
                "synthesizer_model": "openrouter/meta-llama/llama-3.3-70b-instruct",
            }
        return TemplateResponse("research/settings.html", {
            "request": request,
            "prefs": prefs_dict,
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
    from fastapi import TemplateResponse
    from app.models.research import LLMPreference
    try:
        user = await get_current_user_from_cookie(request)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=307)

    async for db in get_db():
        result = await db.execute(select(LLMPreference).where(LLMPreference.user_id == user.id))
        prefs = result.scalar_one_or_none()
        if prefs:
            prefs.provider_type = provider_type
            prefs.provider_api_key = provider_api_key
            prefs.planner_model = planner_model
            prefs.researcher_model = researcher_model
            prefs.synthesizer_model = synthesizer_model
        else:
            prefs = LLMPreference(
                user_id=user.id,
                provider_type=provider_type,
                provider_api_key=provider_api_key,
                planner_model=planner_model,
                researcher_model=researcher_model,
                synthesizer_model=synthesizer_model,
            )
            db.add(prefs)
        await db.commit()

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


# ─── JSON API Endpoints (for Swagger/docs and API clients) ───────────────────

# Railway health probe hits /health — served by the health router
