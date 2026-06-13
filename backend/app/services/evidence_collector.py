"""Evidence Collector — delegates to MCPToolRegistry."""
import structlog
from typing import List
from app.services.text_utils import CREDIBILITY, chunk_text as _chunk_text

log = structlog.get_logger()

class EvidenceCollector:
    async def collect_all(self, company: str, session_id: str) -> List[dict]:
        from app.services.mcp_client import mcp_registry
        return await mcp_registry.run_all_for_company(company)

evidence_collector = EvidenceCollector()
