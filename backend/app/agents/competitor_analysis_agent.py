"""
Competitor Analysis Agent — deep dive per competitor
"""
import structlog
from typing import List
from app.services.llm_client import phi3
from app.services.vector_store import vector_store

log = structlog.get_logger()

SYSTEM = """You are a senior competitive analyst. Provide deep analysis
based only on provided evidence."""

PROMPT = """
Analyze "{competitor}" vs "{company}".

Evidence:
{evidence}

Return JSON:
{{
  "product_comparison": "",
  "pricing_analysis": "",
  "funding_valuation": "",
  "strengths": [],
  "weaknesses": [],
  "market_share_est": "",
  "key_differentiators": []
}}
"""


class CompetitorAnalysisAgent:
    name = "competitor_analysis_agent"

    async def run(self, session_id: str, company: str, competitors: List[str]) -> dict:
        log.info("competitor_analysis_start", competitors=competitors)
        analyses = {}
        for competitor in competitors[:5]:
            chunks = await vector_store.hybrid_search(
                session_id=session_id,
                query=f"{competitor} pricing funding strengths weaknesses products",
                top_k=8,
            )
            evidence = "\n\n".join(f"[{c['source_url']}]\n{c['content']}" for c in chunks)
            result = await phi3.generate_json(
                PROMPT.format(competitor=competitor, company=company, evidence=evidence),
                system=SYSTEM,
            )
            analyses[competitor] = result
        return {"agent": self.name, "company": company,
                "data": {"competitor_analyses": analyses}}
