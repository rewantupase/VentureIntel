from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class ResearchRequest(BaseModel):
    company_name: str = Field(..., description="Company or topic to research")
    user_id: Optional[str] = None
    depth: str = Field(default="standard", description="quick | standard | deep")


class SessionStatus(BaseModel):
    session_id: str
    status: str
    agent_states: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AgentStatusItem(BaseModel):
    agent: str
    status: str
    progress: int
    result_preview: Optional[str] = None


class ReportSummary(BaseModel):
    session_id: str
    company_name: str
    created_at: datetime
    pdf_available: bool


class RiskItem(BaseModel):
    category: str
    severity: str  # low | medium | high
    score: float
    description: str
    evidence: List[str] = []


class CompetitorProfile(BaseModel):
    name: str
    market_position: Optional[str] = None
    strengths: List[str] = []
    weaknesses: List[str] = []
    funding: Optional[str] = None
    market_share_est: Optional[str] = None


class VerifiedFinding(BaseModel):
    claim: str
    source_url: str
    confidence_score: float
    source_quality: float


class FullReport(BaseModel):
    company_profile: Dict[str, Any]
    market_analysis: Dict[str, Any]
    competitors: List[CompetitorProfile]
    risks: List[RiskItem]
    verified_findings: List[VerifiedFinding]
    conclusions: str
    sources: List[Dict[str, str]]


class ChatMessage(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    sources: List[str] = []
