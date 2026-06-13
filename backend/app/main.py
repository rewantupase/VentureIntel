"""
FastAPI Gateway — Competitor Intelligence Platform
Local dev: SQLite + embedded ChromaDB + BackgroundTasks (no Docker/Celery needed)
Production: PostgreSQL + ChromaDB container + Celery workers
"""
import uuid, os, json
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from prometheus_fastapi_instrumentator import Instrumentator
import structlog

from app.config import settings
from app.database import get_db, init_db
from app.models.schemas import ResearchRequest, ChatMessage, ChatResponse
from app.models.db_models import ResearchSession, AgentResult, Report, RiskScore
from app.services.llm_client import phi3
from app.services.vector_store import vector_store
from app.services.mcp_client import mcp_registry

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup: init db")
    await init_db()
    log.info("startup: db ready")
    log.info("startup: mcp_tools", tools=mcp_registry.list_tools())
    yield
    log.info("shutdown")


app = FastAPI(
    title="Competitor Intelligence API",
    description="LangGraph multi-agent competitive intelligence — local Phi-3 + ChromaDB + MCP",
    version="2.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                  allow_methods=["*"], allow_headers=["*"])
Instrumentator().instrument(app).expose(app)


# ── Background pipeline ───────────────────────────────────────────────────────
async def _run_pipeline(session_id: str, company: str):
    from app.database import AsyncSessionLocal
    from app.agents.orchestrator import AgentOrchestrator
    async with AsyncSessionLocal() as db:
        orch = AgentOrchestrator(db)
        try:
            await orch.run_pipeline(session_id, company)
        except Exception as e:
            log.error("pipeline_failed", error=str(e), session_id=session_id)
            async with AsyncSessionLocal() as db2:
                await db2.execute(
                    text("UPDATE research_sessions SET status='failed' WHERE id=:id"),
                    {"id": session_id}
                )
                await db2.commit()


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "phi3_available": await phi3.health_check(),
        "phi3_model": settings.OLLAMA_MODEL,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/llm/status")
async def llm_status():
    return {
        "model": settings.OLLAMA_MODEL,
        "ollama_url": settings.OLLAMA_URL,
        "available": await phi3.health_check(),
    }


@app.get("/api/chroma/status")
async def chroma_status():
    try:
        from app.services.vector_store import _get_client
        cols = _get_client().list_collections()
        return {"status": "ok", "collections": len(cols),
                "mode": "http" if os.getenv("CHROMA_HOST") else "embedded"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/api/mcp/tools")
async def mcp_tools():
    """List all registered MCP tools and their status."""
    return {"tools": mcp_registry.tool_manifest()}


@app.get("/api/graph/schema")
async def graph_schema():
    """Return the LangGraph node/edge schema for visualisation."""
    return {
        "nodes": ["collect_evidence", "parallel_agents",
                  "competitor_analysis", "verification", "report"],
        "edges": [
            {"from": "collect_evidence",   "to": "parallel_agents"},
            {"from": "parallel_agents",    "to": "competitor_analysis",
             "note": "fan-out: research + discovery + risk run in parallel"},
            {"from": "competitor_analysis","to": "verification"},
            {"from": "verification",       "to": "report",
             "note": "deterministic cross-source — no LLM"},
            {"from": "report",             "to": "END"},
        ],
        "parallel_nodes": ["research_node", "discovery_node", "risk_node"],
        "verification_method": "cross_source_fuzzy_match",
    }


# ── Research sessions ─────────────────────────────────────────────────────────
@app.post("/api/research", status_code=202)
async def start_research(req: ResearchRequest, bg: BackgroundTasks,
                          db: AsyncSession = Depends(get_db)):
    sid = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO research_sessions (id, query, status, agent_states) "
             "VALUES (:id, :q, 'queued', '{}')"),
        {"id": sid, "q": req.company_name},
    )
    await db.commit()
    bg.add_task(_run_pipeline, sid, req.company_name)
    log.info("research_started", session_id=sid, company=req.company_name)
    return {"session_id": sid, "status": "queued", "company": req.company_name}


@app.get("/api/research/{session_id}/status")
async def get_status(session_id: str, db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        text("SELECT id, query, status, created_at, updated_at FROM research_sessions WHERE id=:id"),
        {"id": session_id},
    )
    s = row.fetchone()
    if not s:
        raise HTTPException(404, "Session not found")

    agents_row = await db.execute(
        text("SELECT agent_name, status, created_at FROM agent_results WHERE session_id=:id"),
        {"id": session_id},
    )
    agents = [{"name": a[0], "status": a[1], "completed_at": a[2]}
              for a in agents_row.fetchall()]

    return {
        "session_id":  session_id,
        "status":      s[2],
        "company":     s[1],
        "created_at":  s[3],
        "updated_at":  s[4],
        "agents":      agents,
    }


@app.get("/api/research/{session_id}/report")
async def get_report(session_id: str, db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        text("SELECT company_name, report_json, pdf_path, created_at FROM reports WHERE session_id=:id"),
        {"id": session_id},
    )
    r = row.fetchone()
    if not r:
        raise HTTPException(404, "Report not ready yet")

    risks_row = await db.execute(
        text("SELECT category, severity, score FROM risk_scores WHERE session_id=:id"),
        {"id": session_id},
    )
    risk_scores = [{"category": x[0], "severity": x[1], "score": x[2]}
                   for x in risks_row.fetchall()]

    agents_row = await db.execute(
        text("SELECT agent_name, result FROM agent_results WHERE session_id=:id"),
        {"id": session_id},
    )
    agents = {}
    for ag_name, ag_result in agents_row.fetchall():
        try:
            agents[ag_name] = json.loads(ag_result) if isinstance(ag_result, str) else ag_result
        except Exception:
            agents[ag_name] = {}

    report_json = r[1]
    if isinstance(report_json, str):
        try: report_json = json.loads(report_json)
        except: pass

    return {
        "session_id":   session_id,
        "company_name": r[0],
        "created_at":   r[3],
        "pdf_available": bool(r[2] and os.path.exists(r[2] or "")),
        "report":       report_json,
        "risk_scores":  risk_scores,
        "agents":       agents,
    }


@app.get("/api/research/{session_id}/pdf")
async def download_pdf(session_id: str, db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        text("SELECT company_name, pdf_path FROM reports WHERE session_id=:id"),
        {"id": session_id},
    )
    r = row.fetchone()
    if not r or not r[1]:
        raise HTTPException(404, "PDF not available")
    if not os.path.exists(r[1]):
        raise HTTPException(404, "PDF file missing on disk")
    return FileResponse(path=r[1], media_type="application/pdf",
                        filename=f"{r[0]}_intel_report.pdf")


@app.get("/api/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        text("SELECT id, query, status, created_at FROM research_sessions "
             "ORDER BY created_at DESC LIMIT 50")
    )
    return [{"session_id": str(r[0]), "company": r[1],
             "status": r[2], "created_at": r[3]}
            for r in rows.fetchall()]


# ── Chat / RAG ────────────────────────────────────────────────────────────────
@app.post("/api/chat")
async def chat(msg: ChatMessage, db: AsyncSession = Depends(get_db)):
    chunks = await vector_store.hybrid_search(
        session_id=msg.session_id, query=msg.message, top_k=6
    )
    context = "\n\n".join(f"[{c['source_url']}]\n{c['content']}" for c in chunks)
    prompt  = f"Evidence:\n{context}\n\nQuestion: {msg.message}\n\nAnswer:"
    response = await phi3.generate(
        prompt,
        system="You are a helpful competitive intelligence analyst. Base answers only on provided evidence.",
        temperature=0.2, max_tokens=1024,
    )
    return ChatResponse(response=response, sources=[c["source_url"] for c in chunks])


@app.post("/api/chat/stream")
async def chat_stream(msg: ChatMessage, db: AsyncSession = Depends(get_db)):
    chunks  = await vector_store.hybrid_search(
        session_id=msg.session_id, query=msg.message, top_k=6
    )
    context = "\n\n".join(f"[{c['source_url']}]\n{c['content']}" for c in chunks)
    prompt  = f"Evidence:\n{context}\n\nQuestion: {msg.message}\nAnswer:"

    async def stream():
        async for token in phi3.stream(prompt):
            yield token

    return StreamingResponse(stream(), media_type="text/plain")
