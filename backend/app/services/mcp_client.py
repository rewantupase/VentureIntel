"""
MCP Client Layer
================
Wraps each external data source as an MCP-style tool with a unified interface.
Each tool returns List[dict] chunks with source metadata.

In production: swap _http_call stubs for real MCP server connections via
  langchain_mcp_adapters or direct SSE transport.
Here: implemented as direct async HTTP calls to the same APIs,
  but wrapped in the MCP tool contract so they're swappable.
"""
import httpx
import json
import structlog
import os
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass, field
from app.services.text_utils import CREDIBILITY, chunk_text as _chunk_text

log = structlog.get_logger()


# ── MCP Tool contract ─────────────────────────────────────────────────────────

@dataclass
class MCPTool:
    name: str
    description: str
    source_type: str
    credibility: int
    _fn: Callable

    async def call(self, **kwargs) -> List[dict]:
        try:
            raw = await self._fn(**kwargs)
            log.info("mcp_tool_called", tool=self.name, chunks=len(raw))
            return raw
        except Exception as e:
            log.warning("mcp_tool_failed", tool=self.name, error=str(e))
            return []


# ── Tool implementations ──────────────────────────────────────────────────────

async def _brave_search(query: str) -> List[dict]:
    key = os.getenv("BRAVE_API_KEY", "")
    if not key:
        return _demo_chunks(query, "brave_search", CREDIBILITY["unknown_blog"])
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": key},
            params={"q": query, "count": 10},
        )
        r.raise_for_status()
        items = r.json().get("web", {}).get("results", [])
        return [
            {"content": f"{i['title']}: {i.get('description','')}",
             "source_url": i["url"], "source_type": "brave_search",
             "credibility_score": CREDIBILITY["unknown_blog"],
             "metadata": {"title": i["title"]}}
            for i in items
        ]


async def _firecrawl_scrape(url: str) -> List[dict]:
    key = os.getenv("FIRECRAWL_API_KEY", "")
    if not key:
        return []
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(
            "https://api.firecrawl.dev/v0/scrape",
            headers={"Authorization": f"Bearer {key}"},
            json={"url": url, "pageOptions": {"onlyMainContent": True}},
        )
        r.raise_for_status()
        content = r.json().get("data", {}).get("content", "")
        return [
            {"content": ch, "source_url": url, "source_type": "official_website",
             "credibility_score": CREDIBILITY["official_website"], "metadata": {}}
            for ch in _chunk_text(content)
        ]


async def _tavily_search(query: str) -> List[dict]:
    key = os.getenv("TAVILY_API_KEY", "")
    if not key:
        return _demo_chunks(query, "tavily", CREDIBILITY["news_tier1"])
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            "https://api.tavily.com/search",
            json={"api_key": key, "query": query,
                  "search_depth": "advanced", "max_results": 8,
                  "include_raw_content": True},
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        out = []
        for res in results:
            content = res.get("raw_content") or res.get("content", "")
            for ch in _chunk_text(content):
                out.append({"content": ch, "source_url": res["url"],
                             "source_type": "tavily",
                             "credibility_score": CREDIBILITY["news_tier1"],
                             "metadata": {"title": res.get("title", "")}})
        return out


async def _reddit_search(query: str) -> List[dict]:
    cid = os.getenv("REDDIT_CLIENT_ID", "")
    secret = os.getenv("REDDIT_CLIENT_SECRET", "")
    if not cid:
        return _demo_chunks(query, "reddit", CREDIBILITY["reddit"])
    import praw
    reddit = praw.Reddit(client_id=cid, client_secret=secret, user_agent="IntelBot/1.0")
    posts = list(reddit.subreddit("all").search(query, limit=5))
    return [
        {"content": f"{p.title}: {p.selftext[:500]}",
         "source_url": f"https://reddit.com{p.permalink}",
         "source_type": "reddit", "credibility_score": CREDIBILITY["reddit"],
         "metadata": {"score": p.score}}
        for p in posts
    ]


async def _github_search(query: str) -> List[dict]:
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        return []
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(
            "https://api.github.com/search/repositories",
            headers={"Authorization": f"token {token}"},
            params={"q": f"org:{query}", "sort": "stars", "per_page": 5},
        )
        r.raise_for_status()
        return [
            {"content": f"GitHub: {repo['full_name']} — {repo.get('description','')}. Stars: {repo['stargazers_count']}",
             "source_url": repo["html_url"], "source_type": "github",
             "credibility_score": CREDIBILITY["github"],
             "metadata": {"stars": repo["stargazers_count"]}}
            for repo in r.json().get("items", [])
        ]


async def _newsapi_search(query: str) -> List[dict]:
    key = os.getenv("NEWSAPI_KEY", "")
    if not key:
        return _demo_chunks(query + " news", "newsapi", CREDIBILITY["news_tier1"])
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(
            "https://newsapi.org/v2/everything",
            params={"q": query, "sortBy": "relevancy", "pageSize": 10, "apiKey": key},
        )
        r.raise_for_status()
        return [
            {"content": f"{a['title']}: {a.get('description','')}. {a.get('content','')}",
             "source_url": a["url"], "source_type": "news",
             "credibility_score": CREDIBILITY["news_tier1"],
             "metadata": {"source": a.get("source", {}).get("name", "")}}
            for a in r.json().get("articles", [])
        ]


def _demo_chunks(query: str, source: str, cred: int) -> List[dict]:
    """Placeholder when API key not configured."""
    return [{"content": f"[DEMO] Results for '{query}' via {source}. Add API key in .env for real data.",
             "source_url": f"https://example.com/{source}",
             "source_type": source, "credibility_score": cred,
             "metadata": {"demo": True}}]


# ── MCP Tool Registry ─────────────────────────────────────────────────────────

class MCPToolRegistry:
    """
    Central registry of all MCP tools.
    Agents call registry.run(tool_name, **kwargs) — never import tools directly.
    """

    def __init__(self):
        self._tools: Dict[str, MCPTool] = {}
        self._register_all()

    def _register_all(self):
        specs = [
            ("brave_search",    "Web search via Brave Search MCP",       "brave_search",      CREDIBILITY["unknown_blog"], _brave_search),
            ("firecrawl_scrape","Website scraping via Firecrawl MCP",     "official_website",  CREDIBILITY["official_website"], _firecrawl_scrape),
            ("tavily_search",   "Deep search + extract via Tavily MCP",   "tavily",            CREDIBILITY["news_tier1"], _tavily_search),
            ("reddit_search",   "Community insights via Reddit MCP",      "reddit",            CREDIBILITY["reddit"], _reddit_search),
            ("github_search",   "Repo/issue data via GitHub MCP",         "github",            CREDIBILITY["github"], _github_search),
            ("newsapi_search",  "News articles via NewsAPI MCP",          "news",              CREDIBILITY["news_tier1"], _newsapi_search),
        ]
        for name, desc, src, cred, fn in specs:
            self._tools[name] = MCPTool(name=name, description=desc,
                                         source_type=src, credibility=cred, _fn=fn)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def get(self, name: str) -> Optional[MCPTool]:
        return self._tools.get(name)

    async def run(self, tool_name: str, **kwargs) -> List[dict]:
        tool = self._tools.get(tool_name)
        if not tool:
            log.warning("mcp_tool_not_found", name=tool_name)
            return []
        return await tool.call(**kwargs)

    async def run_all_for_company(self, company: str) -> List[dict]:
        """Run all search tools in parallel for a company name."""
        import asyncio
        tasks = [
            self.run("brave_search",   query=f"{company} company overview funding competitors"),
            self.run("tavily_search",  query=f"{company} business model products market"),
            self.run("newsapi_search", query=company),
            self.run("reddit_search",  query=company),
            self.run("github_search",  query=company),
            self.run("firecrawl_scrape", url=f"https://{company.lower().replace(' ','')}.com"),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_chunks = []
        for r in results:
            if isinstance(r, list):
                all_chunks.extend(r)
        log.info("mcp_all_tools_done", total_chunks=len(all_chunks), company=company)
        return all_chunks

    def tool_manifest(self) -> List[dict]:
        """Returns tool descriptions for display in UI/logs."""
        return [
            {"name": t.name, "description": t.description,
             "source_type": t.source_type, "credibility": t.credibility}
            for t in self._tools.values()
        ]


mcp_registry = MCPToolRegistry()
