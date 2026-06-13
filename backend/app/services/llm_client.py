"""
Phi-3 LLM client via Ollama REST API.
Gracefully falls back to structured mock responses when Ollama is unavailable,
so the full pipeline always completes and returns a usable report.
"""
import httpx
import json
import structlog
import os
from typing import AsyncIterator, Optional

log = structlog.get_logger()

# ── Mock data (used when Ollama is not running) ───────────────────────────────
_OFFLINE_NOTE = "⚠️ Phi-3 offline — install Ollama (ollama.ai) and run `ollama pull phi3` for real AI analysis."

_MOCK_RESEARCH = {
    "overview": _OFFLINE_NOTE,
    "founders": "N/A (LLM offline)",
    "funding": "N/A (LLM offline)",
    "products": [_OFFLINE_NOTE],
    "traction": "N/A (LLM offline)",
    "partnerships": "N/A (LLM offline)",
    "recent_news": "N/A (LLM offline)",
}
_MOCK_DISCOVERY = {
    "top_competitors": [{"name": "Competitor A", "description": "Mock — LLM offline", "reason_competitor": "N/A"}],
    "industry": "Unknown (LLM offline)",
    "market_position": "Unknown (LLM offline)",
    "similar_products": ["N/A (LLM offline)"],
    "substitutes": ["N/A (LLM offline)"],
}
_MOCK_RISK = {
    "customer_complaints": {"severity": "low", "summary": _OFFLINE_NOTE, "examples": []},
    "product_issues":      {"severity": "low", "summary": _OFFLINE_NOTE, "examples": []},
    "legal_compliance":    {"severity": "low", "summary": _OFFLINE_NOTE, "examples": []},
    "layoffs_funding":     {"severity": "low", "summary": _OFFLINE_NOTE, "examples": []},
    "security_concerns":   {"severity": "low", "summary": _OFFLINE_NOTE, "examples": []},
    "social_sentiment":    {"overall": "neutral", "score": 0.5, "summary": _OFFLINE_NOTE},
    "reputation_risk":     {"severity": "low", "summary": _OFFLINE_NOTE},
    "overall_risk_score":  0.0,
}
_MOCK_EXEC = {
    "executive_summary": _OFFLINE_NOTE,
    "key_conclusions": [
        "Install Ollama from https://ollama.ai",
        "Run: ollama pull phi3",
        "Restart this server, then resubmit your query.",
    ],
}

def _mock_for_prompt(prompt: str) -> dict:
    p = prompt.lower()
    if "executive_summary" in p or "key_conclusions" in p:
        return _MOCK_EXEC
    if "top_competitors" in p and "industry" in p:
        return _MOCK_DISCOVERY
    if "overall_risk_score" in p:
        return _MOCK_RISK
    if "product_comparison" in p or "pricing_analysis" in p:
        return {"product_comparison": _OFFLINE_NOTE, "pricing_analysis": "N/A",
                "funding_valuation": "N/A", "strengths": [_OFFLINE_NOTE],
                "weaknesses": ["N/A"], "market_share_est": "N/A", "key_differentiators": ["N/A"]}
    if "claims" in p and "extract" in p:
        return {"claims": [_OFFLINE_NOTE]}
    if "confidence_score" in p and "supported" in p:
        return {"claim": "N/A", "supported": "no", "confidence_score": 0.0,
                "source_quality_score": 0.0, "contradiction": ""}
    return _MOCK_RESEARCH


class Phi3Client:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model    = os.getenv("OLLAMA_MODEL", "phi3")
        self.timeout  = httpx.Timeout(90.0, connect=5.0)
        self._available: Optional[bool] = None  # cached after first check

    async def _is_available(self) -> bool:
        if self._available is not None:
            return self._available
        self._available = await self.health_check()
        return self._available

    async def generate(self, prompt: str, system: Optional[str] = None,
                       temperature: float = 0.1, max_tokens: int = 2048) -> str:
        """Generate text. Returns mock string if Ollama is offline."""
        if not await self._is_available():
            return _OFFLINE_NOTE

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                return resp.json()["message"]["content"]
        except Exception as e:
            log.warning("phi3_generate_failed", error=str(e))
            self._available = False  # stop retrying this session
            return _OFFLINE_NOTE

    async def generate_json(self, prompt: str, system: Optional[str] = None,
                            temperature: float = 0.05) -> dict:
        """Generate JSON. Returns structured mock dict if Ollama is offline."""
        if not await self._is_available():
            return _mock_for_prompt(prompt)

        json_system = (system or "") + "\nRespond ONLY with valid JSON. No markdown, no explanation."
        try:
            raw = await self.generate(prompt, system=json_system, temperature=temperature)
            if raw == _OFFLINE_NOTE:
                return _mock_for_prompt(prompt)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip().rstrip("`"))
        except Exception as e:
            log.warning("phi3_json_parse_failed", error=str(e))
            return _mock_for_prompt(prompt)

    async def stream(self, prompt: str, system: Optional[str] = None,
                     temperature: float = 0.2) -> AsyncIterator[str]:
        """Streaming generation. Yields mock message if Ollama is offline."""
        if not await self._is_available():
            yield _OFFLINE_NOTE
            return

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self.model, "messages": messages, "stream": True,
                   "options": {"temperature": temperature}}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                    async for line in resp.aiter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                if token := chunk.get("message", {}).get("content", ""):
                                    yield token
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            log.warning("phi3_stream_failed", error=str(e))
            yield _OFFLINE_NOTE

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(3.0)) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                models = [m["name"] for m in resp.json().get("models", [])]
                return any("phi3" in m.lower() or "phi-3" in m.lower() for m in models)
        except Exception:
            return False


phi3 = Phi3Client()
