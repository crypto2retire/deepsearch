from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from app.config import get_settings
from app.database import _get_engine, _get_session_maker, Base
from app.api.routes import auth, research, settings as settings_router, health

settings = get_settings()
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run migrations on startup (skip if DATABASE_URL not configured)
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


@app.get("/", status_code=307)
async def root():
    """Root redirect to /health for Railway load balancer health checks."""
    return RedirectResponse(url="/health")


@app.get("/health")
async def health_root():
    return {"status": "ok", "service": "deepsearch"}
