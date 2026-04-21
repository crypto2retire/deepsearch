import json
import logging
import uuid
from fastapi import APIRouter, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import Column, String, Text, DateTime, Enum as SAEnum
import enum
from app.database import Base
from sse_starlette.sse import EventSourceResponse
from app.agents.coding_pipeline import run_coding_pipeline
from fastapi.templating import Jinja2Templates
import os

logger = logging.getLogger("deepsearch.coding")

router = APIRouter(prefix="/coding", tags=["coding"])
templates = Jinja2Templates(directory="app/templates")


class CodingStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class CodingSession(Base):
    __tablename__ = "coding_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    description = Column(Text, nullable=False)
    github_url = Column(Text, nullable=True)
    status = Column(SAEnum(CodingStatus), default=CodingStatus.PENDING)
    created_at = Column(DateTime, default=__import__("datetime").datetime.utcnow)
    files_json = Column(Text, nullable=True)
    repo_url = Column(Text, nullable=True)


_in_memory_sessions: dict = {}


def _get_zai_key() -> str:
    return os.environ.get("ZAI_API_KEY", "") or os.environ.get("Z.AI_API_KEY", "")


def _get_moonshot_key() -> str:
    return os.environ.get("MOONSHOT_API_KEY", "")


def _get_github_pat() -> str:
    return os.environ.get("GITHUB_PAT", "")


@router.get("", response_class=RedirectResponse)
async def coding_index():
    return RedirectResponse(url="/coding/dashboard", status_code=307)


@router.get("/dashboard", response_class=HTMLResponse)
async def coding_dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "coding/dashboard.html",
        {},
    )


@router.post("/start", status_code=201)
async def start_coding(description: str = Form(...), github_url: str = Form("")) -> JSONResponse:
    zai_key = _get_zai_key()
    if not zai_key:
        raise HTTPException(status_code=400, detail="Z.ai API key not set. Add ZAI_API_KEY in Railway environment variables.")

    moonshot_key = _get_moonshot_key()
    if not moonshot_key:
        raise HTTPException(status_code=400, detail="Moonshot API key not set. Add MOONSHOT_API_KEY in Railway environment variables.")

    github_pat = _get_github_pat()
    if not github_pat:
        raise HTTPException(status_code=400, detail="GitHub PAT not set. Add GITHUB_PAT in Railway environment variables.")

    session_id = str(uuid.uuid4())
    _in_memory_sessions[session_id] = {
        "id": session_id,
        "description": description,
        "github_url": github_url,
        "status": "pending",
        "files": {},
        "repo_url": None,
    }

    return JSONResponse(
        content={
            "id": session_id,
            "description": description,
            "github_url": github_url,
            "status": "pending",
        },
        media_type="application/json",
    )


@router.get("/{job_id}/stream")
async def stream_coding(job_id: str):
    zai_key = _get_zai_key()
    if not zai_key:
        raise HTTPException(status_code=400, detail="Z.ai API key not set")

    moonshot_key = _get_moonshot_key()
    if not moonshot_key:
        raise HTTPException(status_code=400, detail="Moonshot API key not set")

    github_pat = _get_github_pat()
    if not github_pat:
        raise HTTPException(status_code=400, detail="GitHub PAT not set")

    if job_id not in _in_memory_sessions:
        raise HTTPException(status_code=404, detail="Coding job not found")

    session = _in_memory_sessions[job_id]
    session["status"] = "active"

    async def event_generator():
        try:
            async for event in run_coding_pipeline(
                description=session["description"],
                github_url=session.get("github_url") or None,
                zai_api_key=zai_key,
                moonshot_api_key=moonshot_key,
                github_pat=github_pat,
            ):
                logger.info(f"SSE event: agent={event.get('agent')} status={event.get('status')}")

                if event.get("status") in ("completed", "error"):
                    session["status"] = "completed" if event.get("status") == "completed" else "failed"
                    if event.get("files"):
                        session["files"] = event["files"]
                    if event.get("repo_url"):
                        session["repo_url"] = event["repo_url"]

                yield {"event": "update", "data": json.dumps(event)}

            session["status"] = "completed"
            yield {"event": "done", "data": "{}"}

        except Exception as e:
            logger.error(f"Coding pipeline exception: {e}", exc_info=True)
            session["status"] = "failed"
            yield {"event": "error", "data": json.dumps({"message": str(e)})}
            yield {"event": "done", "data": "{}"}

    return EventSourceResponse(
        event_generator(),
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@router.get("/{job_id}", response_class=HTMLResponse)
async def get_coding(request: Request, job_id: str):
    if job_id not in _in_memory_sessions:
        raise HTTPException(status_code=404, detail="Coding job not found")

    session = _in_memory_sessions[job_id]

    return templates.TemplateResponse(
        request,
        "coding/result.html",
        {
            "job_id": job_id,
            "description": session["description"],
            "github_url": session.get("github_url") or "",
            "status": session["status"],
            "files": session.get("files", {}),
            "repo_url": session.get("repo_url") or "",
        },
    )