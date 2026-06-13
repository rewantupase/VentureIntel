"""
Risk Analysis Agent — sentiment and risk scoring
"""
import structlog
from app.services.llm_client import phi3
from app.services.vector_store import vector_store

log = structlog.get_logger()

SYSTEM = """You are a risk analyst. Identify risks from evidence only.
Severity must be: low, medium, or high."""

PROMPT = """
Analyze risk signals for "{company}":

{evidence}

Return JSON:
{{
  "customer_complaints": {{"severity": "low|medium|high", "summary": "", "examples": []}},
  "product_issues":      {{"severity": "low|medium|high", "summary": "", "examples": []}},
  "legal_compliance":    {{"severity": "low|medium|high", "summary": "", "examples": []}},
  "layoffs_funding":     {{"severity": "low|medium|high", "summary": "", "examples": []}},
  "security_concerns":   {{"severity": "low|medium|high", "summary": "", "examples": []}},
  "social_sentiment":    {{"overall": "positive|neutral|negative", "score": 0.0, "summary": ""}},
  "reputation_risk":     {{"severity": "low|medium|high", "summary": ""}},
  "overall_risk_score":  0.0
}}
overall_risk_score: 0.0 (no risk) to 10.0 (extreme risk).
"""


class RiskAnalysisAgent:
    name = "risk_analysis_agent"

    async def run(self, session_id: str, company: str) -> dict:
        log.info("risk_analysis_start", company=company)
        chunks = await vector_store.hybrid_search(
            session_id=session_id,
            query=f"{company} complaints lawsuit legal risk layoffs security breach negative",
            top_k=14,
        )
        evidence = "\n\n".join(f"[{c['source_url']}]\n{c['content']}" for c in chunks)
        result = await phi3.generate_json(
            PROMPT.format(company=company, evidence=evidence), system=SYSTEM
        )
        log.info("risk_analysis_done", score=result.get("overall_risk_score"))
        return {"agent": self.name, "company": company, "data": result,
                "sources": [c["source_url"] for c in chunks]}
