from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.research import LLMPreference
from app.schemas.settings import LLMPrefsIn, LLMPrefsOut
from app.api.deps import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/llm", response_model=LLMPrefsOut)
async def get_llm_prefs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMPreference).where(LLMPreference.user_id == user.id))
    prefs = result.scalar_one_or_none()
    if not prefs:
        raise HTTPException(status_code=404, detail="LLM preferences not set yet")
    return prefs


@router.put("/llm", response_model=LLMPrefsOut)
async def set_llm_prefs(
    data: LLMPrefsIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LLMPreference).where(LLMPreference.user_id == user.id))
    prefs = result.scalar_one_or_none()
    if prefs:
        prefs.planner_model = data.planner_model
        prefs.researcher_model = data.researcher_model
        prefs.synthesizer_model = data.synthesizer_model
        prefs.provider_api_key = data.provider_api_key
        prefs.provider_type = data.provider_type
    else:
        prefs = LLMPreference(
            user_id=user.id,
            planner_model=data.planner_model,
            researcher_model=data.researcher_model,
            synthesizer_model=data.synthesizer_model,
            provider_api_key=data.provider_api_key,
            provider_type=data.provider_type,
        )
        db.add(prefs)
    await db.commit()
    await db.refresh(prefs)
    return prefs
