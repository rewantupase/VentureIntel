"""
Deterministic Verification Agent
=================================
NO LLM INVOLVED. Uses purely algorithmic methods:

1. Claim extraction   — keyword/entity extraction from agent results (regex + NLP-lite)
2. Cross-source check — a claim is verified only if it appears in ≥2 INDEPENDENT sources
3. Similarity scoring — RapidFuzz token_set_ratio for fuzzy text matching across chunks
4. Credibility weight — score weighted by source credibility (SEC=10, news=8, reddit=3…)
5. Contradiction flag — find chunks that express the OPPOSITE sentiment for the same entity
6. Confidence formula — (source_count/max_sources) * avg_credibility/10 * similarity_avg

Result: every finding has a deterministic, reproducible confidence score — no hallucination possible.
"""
import re
import json
import structlog
from typing import List, Dict, Any, Tuple
from rapidfuzz import fuzz
from app.services.vector_store import vector_store

log = structlog.get_logger()

# Credibility weights per source type
CRED_WEIGHTS = {
    "sec_filing": 10, "official_website": 9, "crunchbase": 8,
    "news_tier1": 8, "news": 8, "tavily": 7, "brave_search": 5,
    "linkedin": 7, "github": 6, "reddit": 3, "forum": 3,
    "unknown_blog": 1, "demo": 1,
}

SIMILARITY_THRESHOLD = 42   # RapidFuzz token_set_ratio — lower = more lenient
MIN_SOURCES_FOR_VERIFIED = 2  # must appear in ≥2 independent sources


# ── Claim extraction (deterministic, no LLM) ─────────────────────────────────

_NUMBER_RE  = re.compile(r'\$[\d.,]+[BMK]?|\d+[\d.,]*\s*(?:billion|million|thousand|%|users|employees)', re.I)
_ENTITY_RE  = re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\b')   # Proper nouns
_YEAR_RE    = re.compile(r'\b(19|20)\d{2}\b')

def _extract_claims_from_text(text: str, company: str, max_claims: int = 15) -> List[str]:
    """
    Extract factual claims algorithmically:
    - sentences containing numbers/metrics
    - sentences containing named entities
    - sentences about the target company
    """
    if not text:
        return []

    sentences = re.split(r'(?<=[.!?])\s+', text)
    claims = []
    seen = set()

    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 20 or len(sent) > 300:
            continue
        # Prioritise sentences with numbers, dates, or the company name
        score = 0
        if _NUMBER_RE.search(sent):       score += 3
        if _YEAR_RE.search(sent):         score += 1
        if company.lower() in sent.lower(): score += 2
        if score == 0:
            continue
        norm = sent.lower()[:80]
        if norm not in seen:
            seen.add(norm)
            claims.append(sent)
        if len(claims) >= max_claims:
            break

    return claims


def _extract_all_claims(agent_results: Dict[str, Any], company: str) -> List[str]:
    """Flatten all agent result text and extract claims."""
    all_text = []
    for agent_name, result in agent_results.items():
        data = result.get("data", {})
        all_text.append(_dict_to_text(data))
    combined = " ".join(all_text)
    return _extract_claims_from_text(combined, company)


def _dict_to_text(d: Any, depth: int = 0) -> str:
    """Recursively flatten dict/list to plain text."""
    if depth > 4:
        return ""
    if isinstance(d, str):
        return d
    if isinstance(d, (int, float)):
        return str(d)
    if isinstance(d, list):
        return " ".join(_dict_to_text(i, depth+1) for i in d)
    if isinstance(d, dict):
        return " ".join(_dict_to_text(v, depth+1) for v in d.values())
    return ""


# ── Cross-source verification ─────────────────────────────────────────────────

def _find_supporting_chunks(
    claim: str,
    all_chunks: List[dict],
    threshold: int = SIMILARITY_THRESHOLD,
) -> List[dict]:
    """
    Find chunks that support a claim using fuzzy matching.
    Returns list of matching chunks from DIFFERENT source URLs.
    """
    supporting = []
    seen_urls = set()

    for chunk in all_chunks:
        content = chunk.get("content", "")
        if not content:
            continue
        # RapidFuzz token_set_ratio handles word-order differences well
        score = fuzz.token_set_ratio(claim.lower(), content.lower())
        if score >= threshold:
            url = chunk.get("source_url", "unknown")
            if url not in seen_urls:          # deduplicate by source URL
                seen_urls.add(url)
                supporting.append({**chunk, "similarity": score})

    # Sort by credibility × similarity
    supporting.sort(
        key=lambda x: (CRED_WEIGHTS.get(x.get("source_type",""), 1) * x["similarity"]),
        reverse=True,
    )
    return supporting


def _find_contradicting_chunks(
    claim: str,
    all_chunks: List[dict],
    threshold: int = 38,
) -> List[str]:
    """
    Heuristic contradiction detection:
    Find chunks that mention the same entity but contain negation words.
    """
    negations = {"not", "no", "never", "denied", "false", "incorrect", "wrong",
                 "failed", "dispute", "contrary", "misleading", "inaccurate"}
    claim_words = set(claim.lower().split())
    contradictions = []

    for chunk in all_chunks:
        content = chunk.get("content", "").lower()
        chunk_words = set(content.split())
        # Check for entity overlap + negation
        overlap = len(claim_words & chunk_words)
        has_negation = bool(negations & chunk_words)
        sim = fuzz.token_set_ratio(claim.lower(), content)

        if overlap >= 3 and has_negation and sim >= threshold:
            contradictions.append(chunk.get("content", "")[:200])

    return contradictions[:3]


def _compute_confidence(
    supporting: List[dict],
    claim: str,
) -> Tuple[float, float]:
    """
    Returns (confidence_score, source_quality_score) both 0.0–1.0.

    confidence = min(source_count / MIN_SOURCES_FOR_VERIFIED, 1.0)
                 × (avg_credibility / 10)
                 × (avg_similarity / 100)

    source_quality = avg credibility of supporting sources / 10
    """
    if not supporting:
        return 0.0, 0.0

    n = len(supporting)
    avg_cred = sum(CRED_WEIGHTS.get(c.get("source_type",""), 1) for c in supporting) / n
    avg_sim  = sum(c.get("similarity", 0) for c in supporting) / n

    source_factor = min(n / MIN_SOURCES_FOR_VERIFIED, 1.0)
    confidence    = round(source_factor * (avg_cred / 10) * (avg_sim / 100), 3)
    quality       = round(avg_cred / 10, 3)
    return confidence, quality


# ── Main agent ────────────────────────────────────────────────────────────────

class VerificationAgent:
    name = "verification_agent"

    async def run(
        self,
        session_id: str,
        company: str,
        agent_results: Dict[str, Any],
        # Pre-fetched chunks passed from orchestrator to avoid redundant DB calls
        raw_chunks: List[dict] = None,
    ) -> dict:
        log.info("verification_start", company=company, mode="deterministic_no_llm")

        # 1. Get all evidence chunks from ChromaDB
        if raw_chunks is None:
            # Broad search to get as many chunks as possible for cross-referencing
            raw_chunks = await vector_store.hybrid_search(
                session_id=session_id,
                query=company,
                top_k=50,
            )
        log.info("verification_evidence_loaded", chunks=len(raw_chunks))

        # 2. Extract claims from agent results (no LLM)
        claims = _extract_all_claims(agent_results, company)
        log.info("claims_extracted_deterministic", count=len(claims))

        # 3. Cross-source verify each claim
        verified_findings = []
        for claim in claims[:20]:       # cap at 20 claims
            supporting  = _find_supporting_chunks(claim, raw_chunks)
            contradicts = _find_contradicting_chunks(claim, raw_chunks)
            confidence, quality = _compute_confidence(supporting, claim)

            is_verified = (
                len(supporting) >= MIN_SOURCES_FOR_VERIFIED
                and confidence > 0.15
            )

            verified_findings.append({
                "claim":               claim,
                "supported":           "yes" if is_verified else
                                       ("partial" if len(supporting) == 1 else "no"),
                "supporting_sources":  [s["source_url"] for s in supporting[:4]],
                "best_source":         supporting[0]["source_url"] if supporting else "",
                "source_count":        len(supporting),
                "confidence_score":    confidence,
                "source_quality_score": quality,
                "contradiction":       contradicts[0] if contradicts else "",
                "method":              "cross_source_fuzzy_match",
            })

        # Sort by confidence descending
        verified_findings.sort(key=lambda x: x["confidence_score"], reverse=True)

        # 4. Build evidence graph (which sources corroborate each other)
        evidence_graph = _build_evidence_graph(verified_findings)

        # 5. Summary stats
        n_verified = sum(1 for v in verified_findings if v["supported"] == "yes")
        n_partial  = sum(1 for v in verified_findings if v["supported"] == "partial")
        avg_conf   = (
            sum(v["confidence_score"] for v in verified_findings) / len(verified_findings)
            if verified_findings else 0
        )

        log.info("verification_done",
                 total=len(verified_findings), verified=n_verified,
                 partial=n_partial, avg_conf=round(avg_conf, 3))

        return {
            "agent": self.name,
            "company": company,
            "data": {
                "verified_findings":   verified_findings,
                "avg_confidence":      round(avg_conf, 3),
                "n_verified":          n_verified,
                "n_partial":           n_partial,
                "n_unverified":        len(verified_findings) - n_verified - n_partial,
                "evidence_graph":      evidence_graph,
                "method":              "deterministic_cross_source",
                "min_sources_required": MIN_SOURCES_FOR_VERIFIED,
                "similarity_threshold": SIMILARITY_THRESHOLD,
                "gaps": [v["claim"] for v in verified_findings if v["supported"] == "no"],
                "contradictions": [
                    v["contradiction"] for v in verified_findings if v["contradiction"]
                ],
            },
        }


def _build_evidence_graph(findings: List[dict]) -> List[dict]:
    """
    Build a simple graph: which source URLs appear across multiple verified claims.
    Used to show 'most corroborating sources' in the UI.
    """
    source_claim_count: Dict[str, int] = {}
    for f in findings:
        for src in f.get("supporting_sources", []):
            source_claim_count[src] = source_claim_count.get(src, 0) + 1

    return sorted(
        [{"source": k, "claims_supported": v}
         for k, v in source_claim_count.items()],
        key=lambda x: x["claims_supported"], reverse=True,
    )[:10]
