"""
LangGraph Orchestrator
=======================
Replaces the hand-rolled asyncio.gather orchestrator with a proper StateGraph.

Graph topology:
                     ┌─────────────────────┐
                     │   collect_evidence   │  (MCP tools in parallel)
                     └──────────┬──────────┘
                                │
              ┌─────────────────┼────────────────────┐
              ▼                 ▼                    ▼
      [research_node]   [discovery_node]      [risk_node]   ← parallel fan-out
              └─────────────────┼────────────────────┘
                                │  fan-in (all 3 must complete)
                                ▼
                    [competitor_analysis_node]   (needs discovery output)
                                │
                                ▼
                    [verification_node]          (deterministic, no LLM)
                                │
                                ▼
                    [report_node]
                                │
                                ▼
                             END

Checkpointing: MemorySaver stores state after every node — if a node fails,
resume from last checkpoint without rerunning earlier nodes.
"""
import asyncio
import uuid
import json
import structlog
from datetime import datetime
from typing import Dict, Any, List

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.agents.graph_state import PipelineState
from app.agents.research_agent import ResearchAgent
from app.agents.competitor_discovery_agent import CompetitorDiscoveryAgent
from app.agents.competitor_analysis_agent import CompetitorAnalysisAgent
from app.agents.risk_analysis_agent import RiskAnalysisAgent
from app.agents.verification_agent import VerificationAgent
from app.agents.report_agent import ReportAgent
from app.services.mcp_client import mcp_registry
from app.services.vector_store import vector_store

log = structlog.get_logger()


# ── Node functions ────────────────────────────────────────────────────────────

async def collect_evidence_node(state: PipelineState) -> PipelineState:
    """
    Run all MCP tools in parallel to gather evidence,
    embed and store in ChromaDB.
    """
    company    = state["company"]
    session_id = state["session_id"]
    log.info("node:collect_evidence", company=company)

    chunks = await mcp_registry.run_all_for_company(company)

    if chunks:
        stored = await vector_store.add_chunks(session_id, chunks)
    else:
        stored = 0

    log.info("node:collect_evidence_done", chunks=len(chunks), stored=stored)
    return {
        "raw_chunks":    chunks,
        "chunks_stored": stored,
        "status":        "evidence_collected",
        "completed_nodes": ["collect_evidence"],
    }


async def research_node(state: PipelineState) -> PipelineState:
    log.info("node:research")
    try:
        result = await ResearchAgent().run(state["session_id"], state["company"])
        return {"research": result, "completed_nodes": ["research"],
                "status": "research_done"}
    except Exception as e:
        log.error("node:research_error", error=str(e))
        return {"errors": [f"research: {e}"], "research": {}, "completed_nodes": ["research"]}


async def discovery_node(state: PipelineState) -> PipelineState:
    log.info("node:discovery")
    try:
        result = await CompetitorDiscoveryAgent().run(state["session_id"], state["company"])
        # Extract competitor names for the next node
        names = [
            c.get("name", "") for c in
            result.get("data", {}).get("top_competitors", [])
            if isinstance(c, dict) and c.get("name")
        ]
        return {"discovery": result, "competitor_names": names,
                "completed_nodes": ["discovery"], "status": "discovery_done"}
    except Exception as e:
        log.error("node:discovery_error", error=str(e))
        return {"errors": [f"discovery: {e}"], "discovery": {},
                "competitor_names": [], "completed_nodes": ["discovery"]}


async def risk_node(state: PipelineState) -> PipelineState:
    log.info("node:risk")
    try:
        result = await RiskAnalysisAgent().run(state["session_id"], state["company"])
        return {"risk": result, "completed_nodes": ["risk"], "status": "risk_done"}
    except Exception as e:
        log.error("node:risk_error", error=str(e))
        return {"errors": [f"risk: {e}"], "risk": {}, "completed_nodes": ["risk"]}


async def competitor_analysis_node(state: PipelineState) -> PipelineState:
    log.info("node:competitor_analysis", competitors=state.get("competitor_names", []))
    try:
        result = await CompetitorAnalysisAgent().run(
            state["session_id"],
            state["company"],
            state.get("competitor_names", []),
        )
        return {"competitor_analysis": result,
                "completed_nodes": ["competitor_analysis"],
                "status": "analysis_done"}
    except Exception as e:
        log.error("node:analysis_error", error=str(e))
        return {"errors": [f"competitor_analysis: {e}"],
                "competitor_analysis": {}, "completed_nodes": ["competitor_analysis"]}


async def verification_node(state: PipelineState) -> PipelineState:
    """Deterministic cross-source verification — no LLM."""
    log.info("node:verification")
    try:
        agent_results = {
            "research":            state.get("research", {}),
            "discovery":           state.get("discovery", {}),
            "risk":                state.get("risk", {}),
            "competitor_analysis": state.get("competitor_analysis", {}),
        }
        result = await VerificationAgent().run(
            session_id=state["session_id"],
            company=state["company"],
            agent_results=agent_results,
            raw_chunks=state.get("raw_chunks", []),
        )
        return {"verification": result,
                "completed_nodes": ["verification"],
                "status": "verified"}
    except Exception as e:
        log.error("node:verification_error", error=str(e))
        return {"errors": [f"verification: {e}"],
                "verification": {}, "completed_nodes": ["verification"]}


async def report_node(state: PipelineState) -> PipelineState:
    log.info("node:report")
    try:
        all_results = {
            "research_agent":            state.get("research", {}),
            "competitor_discovery_agent": state.get("discovery", {}),
            "competitor_analysis_agent": state.get("competitor_analysis", {}),
            "risk_analysis_agent":       state.get("risk", {}),
            "verification_agent":        state.get("verification", {}),
        }
        result = await ReportAgent().run(
            state["session_id"], state["company"], all_results
        )
        return {"report": result,
                "completed_nodes": ["report"],
                "status": "completed"}
    except Exception as e:
        log.error("node:report_error", error=str(e))
        return {"errors": [f"report: {e}"],
                "report": {}, "completed_nodes": ["report"],
                "status": "completed"}


# ── Parallel fan-out/fan-in via subgraph ──────────────────────────────────────

async def parallel_agents_node(state: PipelineState) -> PipelineState:
    """
    LangGraph runs nodes sequentially by default.
    We manually run the three parallel agents with asyncio.gather here,
    then merge results back into state — same as a parallel branch subgraph.
    """
    log.info("node:parallel_agents_start")
    results = await asyncio.gather(
        research_node(state),
        discovery_node(state),
        risk_node(state),
        return_exceptions=True,
    )

    merged: PipelineState = {
        "completed_nodes": [],
        "errors": [],
        "research": {}, "discovery": {}, "risk": {},
        "competitor_names": [],
    }
    for r in results:
        if isinstance(r, Exception):
            merged["errors"].append(str(r))
        elif isinstance(r, dict):
            for k, v in r.items():
                if k in ("completed_nodes", "errors") and isinstance(v, list):
                    merged[k] = merged.get(k, []) + v
                else:
                    merged[k] = v

    log.info("node:parallel_agents_done",
             completed=merged.get("completed_nodes", []))
    return merged


# ── Build the LangGraph StateGraph ───────────────────────────────────────────

def build_pipeline_graph() -> Any:
    """
    Constructs and compiles the LangGraph StateGraph.
    Returns a compiled graph ready for .ainvoke().
    """
    builder = StateGraph(PipelineState)

    # Add nodes
    builder.add_node("collect_evidence",      collect_evidence_node)
    builder.add_node("parallel_agents",       parallel_agents_node)
    builder.add_node("competitor_analysis",   competitor_analysis_node)
    builder.add_node("verification",          verification_node)
    builder.add_node("report",                report_node)

    # Entry point
    builder.set_entry_point("collect_evidence")

    # Edges (directed acyclic pipeline)
    builder.add_edge("collect_evidence",    "parallel_agents")
    builder.add_edge("parallel_agents",     "competitor_analysis")
    builder.add_edge("competitor_analysis", "verification")
    builder.add_edge("verification",        "report")
    builder.add_edge("report",              END)

    # MemorySaver checkpointer — persists state after every node
    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    log.info("langgraph_compiled", nodes=list(builder.nodes))
    return graph


# Singleton compiled graph
_pipeline_graph = None

def get_pipeline_graph():
    global _pipeline_graph
    if _pipeline_graph is None:
        _pipeline_graph = build_pipeline_graph()
    return _pipeline_graph


# ── High-level orchestrator (used by FastAPI + Celery) ───────────────────────

class AgentOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_pipeline(self, session_id: str, company: str) -> Dict[str, Any]:
        log.info("orchestrator_start", session_id=session_id, company=company)

        graph = get_pipeline_graph()

        # LangGraph config — thread_id ties checkpoints to this session
        config = {"configurable": {"thread_id": session_id}}

        initial_state: PipelineState = {
            "session_id":      session_id,
            "company":         company,
            "raw_chunks":      [],
            "completed_nodes": [],
            "errors":          [],
            "status":          "starting",
        }

        await self._set_status(session_id, "running_graph")

        try:
            # Stream node outputs so we can persist each agent result as it completes
            async for event in graph.astream(initial_state, config=config):
                node_name = list(event.keys())[0]
                node_state = event[node_name]
                log.info("graph_node_complete", node=node_name,
                         status=node_state.get("status", ""))

                # Persist agent results to DB as they arrive
                await self._persist_node_output(session_id, company, node_name, node_state)

        except Exception as e:
            log.error("graph_execution_failed", error=str(e))
            await self._set_status(session_id, "failed")
            raise

        # Reconstruct final state from checkpointer
        final = await graph.aget_state(config)
        final_values = final.values if final else {}

        await self._set_status(session_id, "completed")
        log.info("orchestrator_done", session_id=session_id,
                 nodes=final_values.get("completed_nodes", []),
                 errors=final_values.get("errors", []))

        return {
            "session_id":   session_id,
            "company":      company,
            "status":       "completed",
            "completed_nodes": final_values.get("completed_nodes", []),
            "errors":       final_values.get("errors", []),
        }

    async def _persist_node_output(
        self,
        session_id: str,
        company: str,
        node_name: str,
        node_state: dict,
    ):
        """Save each node's output to the DB as it completes."""
        # Map graph node names to agent result keys and DB agent names
        node_to_agent = {
            "parallel_agents":     None,          # meta-node, skip
            "collect_evidence":    None,          # no agent result
            "competitor_analysis": "competitor_analysis_agent",
            "verification":        "verification_agent",
            "report":              "report_agent",
        }

        # Parallel_agents node contains research + discovery + risk
        if node_name == "parallel_agents":
            for key, db_name in [
                ("research",  "research_agent"),
                ("discovery", "competitor_discovery_agent"),
                ("risk",      "risk_analysis_agent"),
            ]:
                data = node_state.get(key, {})
                if data:
                    await self._save_agent(session_id, db_name, data)

        elif node_name == "report":
            report_data = node_state.get("report", {})
            if report_data:
                await self._save_report(session_id, company, report_data)

        elif node_name == "verification":
            vdata = node_state.get("verification", {})
            if vdata:
                await self._save_agent(session_id, "verification_agent", vdata)

        elif node_name == "competitor_analysis":
            adata = node_state.get("competitor_analysis", {})
            if adata:
                await self._save_agent(session_id, "competitor_analysis_agent", adata)

        # Save risk scores from risk agent
        if "risk" in node_state and node_state["risk"]:
            await self._save_risks(session_id, node_state)

    async def _set_status(self, session_id: str, status: str):
        try:
            await self.db.execute(
                text("UPDATE research_sessions SET status=:s, updated_at=:t WHERE id=:id"),
                {"s": status, "t": datetime.utcnow(), "id": session_id},
            )
            await self.db.commit()
        except Exception as e:
            log.warning("set_status_failed", error=str(e))

    async def _save_agent(self, session_id: str, name: str, result: dict):
        try:
            data = result.get("data", result)
            await self.db.execute(
                text("""INSERT OR IGNORE INTO agent_results
                        (id, session_id, agent_name, result, status)
                        VALUES (:id, :sid, :name, :result, 'completed')"""),
                {"id": str(uuid.uuid4()), "sid": session_id,
                 "name": name, "result": json.dumps(data)},
            )
            await self.db.commit()
        except Exception as e:
            log.warning("save_agent_failed", agent=name, error=str(e))

    async def _save_report(self, session_id: str, company: str, result: dict):
        try:
            data = result.get("data", result)
            await self.db.execute(
                text("""INSERT OR IGNORE INTO reports
                        (id, session_id, company_name, report_json, pdf_path)
                        VALUES (:id, :sid, :co, :rj, :pdf)"""),
                {"id": str(uuid.uuid4()), "sid": session_id,
                 "co": company, "rj": json.dumps(data),
                 "pdf": data.get("pdf_path")},
            )
            await self.db.commit()
        except Exception as e:
            log.warning("save_report_failed", error=str(e))

    async def _save_risks(self, session_id: str, node_state: dict):
        risk_data = node_state.get("risk", {}).get("data", {})
        sev_map   = {"low": 2.0, "medium": 5.0, "high": 8.5}
        cats      = ["customer_complaints", "product_issues", "legal_compliance",
                     "layoffs_funding", "security_concerns", "reputation_risk"]
        for cat in cats:
            d = risk_data.get(cat, {})
            if isinstance(d, dict) and d.get("severity"):
                try:
                    await self.db.execute(
                        text("""INSERT OR IGNORE INTO risk_scores
                                (id, session_id, category, severity, score, evidence)
                                VALUES (:id, :sid, :cat, :sev, :score, :ev)"""),
                        {"id": str(uuid.uuid4()), "sid": session_id,
                         "cat": cat, "sev": d["severity"],
                         "score": sev_map.get(d["severity"], 3.0),
                         "ev": json.dumps(d.get("examples", []))},
                    )
                except Exception:
                    pass
        await self.db.commit()
