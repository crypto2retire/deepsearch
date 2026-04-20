import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class SessionStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=True, index=True)
    query = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(SAEnum(SessionStatus), default=SessionStatus.PENDING)
    cost_usd = Column(Integer, default=0)

    findings = relationship("ResearchFinding", back_populates="session")
    answer = relationship("ResearchAnswer", back_populates="session", uselist=False)


class ResearchFinding(Base):
    __tablename__ = "research_findings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("research_sessions.id"), nullable=False, index=True)
    agent = Column(String(50), nullable=False)
    sub_task = Column(Text, nullable=False)
    sources = Column(Text, nullable=True)
    raw_findings = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ResearchSession", back_populates="findings")


class ResearchAnswer(Base):
    __tablename__ = "research_answers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("research_sessions.id"), nullable=False, unique=True)
    answer_markdown = Column(Text, nullable=True)
    citations = Column(Text, nullable=True)
    follow_up_questions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ResearchSession", back_populates="answer")


# ---------------------------------------------------------------------------
# Global settings (single-row table — no user auth required)
# ---------------------------------------------------------------------------

class GlobalSetting(Base):
    """Single-row table storing the active LLM configuration."""
    __tablename__ = "global_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_type = Column(String(50), default="openrouter")
    provider_api_key = Column(String(500), default="")
    planner_model = Column(String(200), default="openrouter/meta-llama/llama-3.1-8b-instruct")
    researcher_model = Column(String(200), default="openrouter/meta-llama/llama-3.3-70b-instruct")
    synthesizer_model = Column(String(200), default="openrouter/meta-llama/llama-3.3-70b-instruct")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
