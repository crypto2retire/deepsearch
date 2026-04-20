import asyncio
import json
import logging
import uuid
from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse
from app.database import get_db
from app.models.research import ResearchSession, ResearchFinding, ResearchAnswer, SessionStatus
from app.agents.pipeline import run_pipeline
from app.services.prefs import get_global_llm_prefs, get_tavily_api_key

logger = logging.getLogger("deepsearch.research")

router = APIRouter(prefix="/research", tags=["research"])


def require_api_key():
    prefs = get_global_llm_prefs()
    key = prefs["provider_api_key"]
    if not key:
        raise HTTPException(status_code=400, detail="Set PROVIDER_API_KEY in Railway environment variables first")
    return key


@router.post("", status_code=201)
async def start_research(query: str = Form(...)) -> JSONResponse:
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
    """Stream SSE events for the research pipeline."""
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

    async def event_generator():
        findings = []
        pipeline_failed = False

        try:
            async for event in run_pipeline(
                query=session.query,
                api_key=api_key,
                planner_model=prefs["planner_model"],
                researcher_model_1=prefs["researcher_model_1"],
                researcher_model_2=prefs["researcher_model_2"],
                synthesizer_model=prefs["synthesizer_model"],
                provider=prefs["provider_type"],
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


@router.get("/{job_id}")
async def get_research(job_id: str) -> dict:
    async for db in get_db():
        result = await db.execute(
            select(ResearchSession)
            .options(selectinload(ResearchSession.answer))
            .where(ResearchSession.id == job_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Research job not found")

        answer_data = None
        if session.answer:
            answer_data = session.answer

        return {
            "id": session.id,
            "query": session.query,
            "answer_markdown": answer_data.answer_markdown if answer_data else None,
            "citations": answer_data.citations if answer_data else None,
            "follow_up_questions": answer_data.follow_up_questions if answer_data else None,
            "status": session.status.value,
        }