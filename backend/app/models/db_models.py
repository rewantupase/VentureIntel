"""
SQLAlchemy ORM models.
Uses String for UUIDs so it works with both SQLite (local dev) and PostgreSQL (prod).
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey, JSON
from app.database import Base


def _uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id       = Column(String(36), primary_key=True, default=_uuid)
    email    = Column(String, unique=True, nullable=False)
    name     = Column(String)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class ResearchSession(Base):
    __tablename__ = "research_sessions"
    id           = Column(String(36), primary_key=True, default=_uuid)
    user_id      = Column(String(36), ForeignKey("users.id"), nullable=True)
    query        = Column(Text, nullable=False)
    status       = Column(String, default="pending")
    agent_states = Column(JSON, default=dict)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentResult(Base):
    __tablename__ = "agent_results"
    id         = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("research_sessions.id"))
    agent_name = Column(String, nullable=False)
    result     = Column(JSON, default=dict)
    status     = Column(String, default="pending")
    error      = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Report(Base):
    __tablename__ = "reports"
    id           = Column(String(36), primary_key=True, default=_uuid)
    session_id   = Column(String(36), ForeignKey("research_sessions.id"))
    company_name = Column(String)
    report_json  = Column(JSON, default=dict)
    pdf_path     = Column(Text)
    created_at   = Column(DateTime, default=datetime.utcnow)


class RiskScore(Base):
    __tablename__ = "risk_scores"
    id         = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("research_sessions.id"))
    category   = Column(String, nullable=False)
    severity   = Column(String, nullable=False)
    score      = Column(Float, nullable=False)
    evidence   = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
