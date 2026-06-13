"""
Competitor Discovery Agent
"""
import structlog
from app.services.llm_client import phi3
from app.services.vector_store import vector_store

log = structlog.get_logger()

SYSTEM = """You are a competitive intelligence specialist. Identify competitors
from evidence only. No hallucination."""

PROMPT = """
Company: "{company}"

Evidence:
{evidence}

Return JSON with keys:
- top_competitors: list of {{name, description, reason_competitor}}
- industry: string
- market_position: string
- similar_products: list of strings
- substitutes: list of strings
"""


class CompetitorDiscoveryAgent:
    name = "competitor_discovery_agent"

    async def run(self, session_id: str, company: str) -> dict:
        log.info("competitor_discovery_start", company=company)
        chunks = await vector_store.hybrid_search(
            session_id=session_id,
            query=f"{company} competitors alternatives similar products market",
            top_k=12,
        )
        evidence = "\n\n".join(f"[{c['source_url']}]\n{c['content']}" for c in chunks)
        result = await phi3.generate_json(
            PROMPT.format(company=company, evidence=evidence), system=SYSTEM
        )
        log.info("competitor_discovery_done", count=len(result.get("top_competitors", [])))
        return {"agent": self.name, "company": company, "data": result,
                "sources": [c["source_url"] for c in chunks]}
