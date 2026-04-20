import asyncio
import json
import logging
import uuid
from fastapi import APIRouter, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse
from app.database import get_db
from app.models.research import ResearchSession, ResearchFinding, ResearchAnswer, SessionStatus
from app.agents.pipeline import run_pipeline
from app.services.prefs import get_global_llm_prefs, get_tavily_api_key
from fastapi.templating import Jinja2Templates

logger = logging.getLogger("deepsearch.research")

router = APIRouter(prefix="/research", tags=["research"])
templates = Jinja2Templates(directory="app/templates")


def require_api_key():
    prefs = get_global_llm_prefs()
    key = prefs["provider_api_key"]
    if not key:
        raise HTTPException(status_code=400, detail="Set PROVIDER_API_KEY in Railway environment variables first")
    return key


@router.post("", status_code=201)
async def start_research(query: str = Form(...), skill: str = Form("general")) -> JSONResponse:
    prefs = get_global_llm_prefs()
    if not prefs["provider_api_key"]:
        raise HTTPException(
            status_code=400,
            detail="PROVIDER_API_KEY not set. Add it in Railway → Variables.",
        )
    async for db in get_db():
        session = ResearchSession(user_id="00000000-0000-0000-0000-000000000000", query=query, status=SessionStatus.PENDING)
        db.add(session)
        await db.commit()
        await db.refresh(session)
        try:
            await db.execute(text("UPDATE research_sessions SET skill = :skill WHERE id = :id"), {"skill": skill, "id": session.id})
            await db.commit()
        except Exception:
            pass
        return JSONResponse(
            content={
                "id": session.id,
                "query": session.query,
                "status": session.status.value,
            },
            media_type="application/json",
        )


@router.get("/{job_id}/stream")
async def stream_research(job_id: str):
    prefs = get_global_llm_prefs()
    api_key = prefs["provider_api_key"]
    if not api_key:
        raise HTTPException(status_code=400, detail="Set PROVIDER_API_KEY in Railway environment variables")

    async for db in get_db():
        result = await db.execute(select(ResearchSession).where(ResearchSession.id == job_id))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Research job not found")

        session.status = SessionStatus.ACTIVE
        await db.commit()

    skill_id = 'general'
    try:
        async for db2 in get_db():
            r = await db2.execute(text("SELECT skill FROM research_sessions WHERE id = :id"), {"id": job_id})
            row = r.fetchone()
            if row and row[0]:
                skill_id = row[0]
    except Exception:
        pass

    async def event_generator():
        findings = []
        pipeline_failed = False

        try:
            async for event in run_pipeline(
                query=session.query,
                default_api_key=api_key,
                default_provider=prefs["provider_type"],
                planner_model=prefs["planner_model"],
                planner_provider=prefs.get("planner_provider", ""),
                planner_api_key=prefs.get("planner_api_key", ""),
                researcher_model_1=prefs["researcher_model_1"],
                researcher_provider_1=prefs.get("researcher_provider_1", ""),
                researcher_api_key_1=prefs.get("researcher_api_key_1", ""),
                researcher_model_2=prefs["researcher_model_2"],
                researcher_provider_2=prefs.get("researcher_provider_2", ""),
                researcher_api_key_2=prefs.get("researcher_api_key_2", ""),
                synthesizer_model=prefs["synthesizer_model"],
                synthesizer_provider=prefs.get("synthesizer_provider", ""),
                synthesizer_api_key=prefs.get("synthesizer_api_key", ""),
                skill_id=skill_id,
            ):
                logger.info(f"SSE event: agent={event.get('agent')} status={event.get('status')}")
                yield {"event": "update", "data": json.dumps(event)}

                if event.get("status") == "error":
                    pipeline_failed = True

                if event["agent"] == "researcher" and event["status"] == "completed":
                    findings = event.get("findings", [])
                    async for db in get_db():
                        for f in findings:
                            finding = ResearchFinding(
                                session_id=session.id,
                                agent="researcher",
                                sub_task=f.get("sub_task", ""),
                                sources=json.dumps(f.get("search_results", [])),
                                raw_findings=json.dumps(f.get("findings", [])),
                            )
                            db.add(finding)
                        await db.commit()

                if event["agent"] == "synthesizer" and event["status"] == "completed":
                    result_data = event.get("result", {})
                    async for db in get_db():
                        answer = ResearchAnswer(
                            session_id=session.id,
                            answer_markdown=result_data.get("answer", ""),
                            citations=json.dumps(result_data.get("sources", [])),
                            follow_up_questions=json.dumps(result_data.get("follow_up_questions", [])),
                        )
                        db.add(answer)
                        session_result = await db.execute(
                            select(ResearchSession).where(ResearchSession.id == job_id)
                        )
                        sess = session_result.scalar_one_or_none()
                        if sess:
                            sess.status = SessionStatus.COMPLETED
                            await db.commit()

        except Exception as e:
            logger.error(f"Pipeline exception: {e}", exc_info=True)
            pipeline_failed = True
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

        if pipeline_failed:
            try:
                async for db in get_db():
                    session_result = await db.execute(
                        select(ResearchSession).where(ResearchSession.id == job_id)
                    )
                    sess = session_result.scalar_one_or_none()
                    if sess and sess.status != SessionStatus.COMPLETED:
                        sess.status = SessionStatus.FAILED
                        await db.commit()
            except Exception:
                logger.error("Failed to update session status to FAILED")

        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(
        event_generator(),
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@router.get("/{job_id}", response_class=HTMLResponse)
async def get_research(request: Request, job_id: str):
    async for db in get_db():
        result = await db.execute(
            select(ResearchSession)
            .options(selectinload(ResearchSession.answer))
            .where(ResearchSession.id == job_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Research job not found")

        answer = None
        citations = []
        follow_ups = []

        if session.answer:
            answer = session.answer.answer_markdown or ""
            try:
                citations = json.loads(session.answer.citations or "[]")
            except (json.JSONDecodeError, TypeError):
                citations = []
            try:
                follow_ups = json.loads(session.answer.follow_up_questions or "[]")
            except (json.JSONDecodeError, TypeError):
                follow_ups = []

        return templates.TemplateResponse(
            request,
            "research/detail.html",
            {
                "query": session.query,
                "status": session.status.value,
                "answer": answer,
                "citations": citations,
                "follow_ups": follow_ups,
            },
        )


@router.post("/clear-history")
async def clear_history():
    async for db in get_db():
        await db.execute(text("DELETE FROM research_findings"))
        await db.execute(text("DELETE FROM research_answers"))
        await db.execute(text("DELETE FROM research_sessions"))
        await db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)
