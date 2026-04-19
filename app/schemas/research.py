from pydantic import BaseModel
from typing import Optional


class ResearchStart(BaseModel):
    query: str


class ResearchJob(BaseModel):
    id: str
    query: str
    status: str


class ResearchStatus(BaseModel):
    id: str
    query: str
    status: str
    cost_usd: float


class ResearchResult(BaseModel):
    id: str
    query: str
    answer_markdown: Optional[str] = None
    citations: Optional[str] = None
    follow_up_questions: Optional[str] = None
    status: str


class ResearchHistory(BaseModel):
    items: list[ResearchResult]
