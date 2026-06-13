"""
Research Agent: Market Intelligence
"""
import structlog
from app.services.llm_client import phi3
from app.services.vector_store import vector_store

log = structlog.get_logger()

SYSTEM = """You are a market intelligence analyst. Extract structured information
from evidence. Be factual — only use what is present in the evidence."""

PROMPT = """
Based on evidence about "{company}", extract:
1. Company Overview (mission, industry, business model)
2. Founders & Leadership
3. Funding & Revenue
4. Products / Services
5. Traction & Milestones
6. Key Partnerships
7. Recent News

Evidence:
{evidence}

Return JSON with keys: overview, founders, funding, products, traction, partnerships, recent_news.
"""


class ResearchAgent:
    name = "research_agent"

    async def run(self, session_id: str, company: str) -> dict:
        log.info("research_agent_start", company=company)
        chunks = await vector_store.hybrid_search(
            session_id=session_id,
            query=f"{company} company overview founders funding products",
            top_k=12,
        )
        evidence = "\n\n".join(f"[{c['source_url']}]\n{c['content']}" for c in chunks)
        result = await phi3.generate_json(
            PROMPT.format(company=company, evidence=evidence), system=SYSTEM
        )
        log.info("research_agent_done", keys=list(result.keys()))
        return {"agent": self.name, "company": company, "data": result,
                "sources": [c["source_url"] for c in chunks]}
