import asyncio
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse
from app.database import get_db
from app.models.user import User
from app.models.research import ResearchSession, ResearchFinding, ResearchAnswer, SessionStatus
from app.schemas.research import ResearchStart, ResearchJob, ResearchResult, ResearchHistory
from app.api.deps import get_current_user
from app.agents.pipeline import run_pipeline

router = APIRouter(prefix="/research", tags=["research"])


@router.post("", status_code=201)
async def start_research(
    data: ResearchStart,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResearchJob:
    # Get user's LLM preferences
    if not user.llm_preferences:
        raise HTTPException(status_code=400, detail="Please set your LLM API key in settings first")

    session = ResearchSession(user_id=user.id, query=data.query, status=SessionStatus.PENDING)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return ResearchJob(id=session.id, query=data.query, status=session.status.value)


@router.get("/{job_id}/stream")
async def stream_research(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify session ownership
    result = await db.execute(select(ResearchSession).where(ResearchSession.id == job_id))
    session = result.scalar_one_or_none()
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Research job not found")

    prefs = user.llm_preferences
    if not prefs:
        raise HTTPException(status_code=400, detail="No LLM preferences set")

    # Update status
    session.status = SessionStatus.ACTIVE
    await db.commit()

    async def event_generator():
        findings = []
        answer_text = ""
        citations_text = ""
        follow_ups_text = ""

        async for event in run_pipeline(
            query=session.query,
            api_key=prefs.provider_api_key,
            planner_model=prefs.planner_model,
            researcher_model=prefs.researcher_model,
            synthesizer_model=prefs.synthesizer_model,
            provider=prefs.provider_type,
        ):
            yield {"event": "update", "data": json.dumps(event)}

            if event["agent"] == "researcher" and event["status"] == "completed":
                findings = event.get("findings", [])
                # Persist findings
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
                answer_text = result_data.get("answer", "")
                citations_text = json.dumps(result_data.get("sources", []))
                follow_ups_text = json.dumps(result_data.get("follow_up_questions", []))

                answer = ResearchAnswer(
                    session_id=session.id,
                    answer_markdown=answer_text,
                    citations=citations_text,
                    follow_up_questions=follow_ups_text,
                )
                db.add(answer)
                session.status = SessionStatus.COMPLETED
                await db.commit()

        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(event_generator())


@router.get("/{job_id}")
async def get_research(job_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> ResearchResult:
    result = await db.execute(select(ResearchSession).where(ResearchSession.id == job_id))
    session = result.scalar_one_or_none()
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Research job not found")

    answer_data = None
    if session.answer:
        answer_data = session.answer

    return ResearchResult(
        id=session.id,
        query=session.query,
        answer_markdown=answer_data.answer_markdown if answer_data else None,
        citations=answer_data.citations if answer_data else None,
        follow_up_questions=answer_data.follow_up_questions if answer_data else None,
        status=session.status.value,
    )


@router.get("")
async def history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> ResearchHistory:
    result = await db.execute(
        select(ResearchSession)
        .where(ResearchSession.user_id == user.id)
        .order_by(ResearchSession.created_at.desc())
        .limit(50)
    )
    sessions = result.scalars().all()
    items = []
    for s in sessions:
        items.append(ResearchResult(
            id=s.id,
            query=s.query,
            answer_markdown=s.answer.answer_markdown if s.answer else None,
            citations=s.answer.citations if s.answer else None,
            follow_up_questions=s.answer.follow_up_questions if s.answer else None,
            status=s.status.value,
        ))
    return ResearchHistory(items=items)
