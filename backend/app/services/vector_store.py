"""
Vector Store — ChromaDB backend.
- In Docker: connects to ChromaDB HTTP server (chromadb service)
- In local dev: uses embedded PersistentClient (no server needed)

Hybrid retrieval: ChromaDB dense ANN + BM25 over candidates + cross-encoder rerank.
"""
import asyncio
import os
import uuid
import structlog
from typing import List
from rank_bm25 import BM25Okapi

log = structlog.get_logger()

_chroma_client = None


def _get_client():
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client

    import chromadb
    from chromadb.config import Settings

    chroma_host = os.getenv("CHROMA_HOST", "")
    chroma_port = int(os.getenv("CHROMA_PORT", "8000"))

    if chroma_host:
        # Docker mode — connect to the chromadb container over HTTP
        log.info("chromadb_http_mode", host=chroma_host, port=chroma_port)
        _chroma_client = chromadb.HttpClient(
            host=chroma_host,
            port=chroma_port,
            settings=Settings(anonymized_telemetry=False),
        )
    else:
        # Local dev mode — embedded, persists to disk
        path = "/tmp/chromadb"
        log.info("chromadb_embedded_mode", path=path)
        _chroma_client = chromadb.PersistentClient(
            path=path,
            settings=Settings(anonymized_telemetry=False),
        )

    return _chroma_client


def _collection_name(session_id: str) -> str:
    # ChromaDB names: 3-63 chars, alphanumeric + hyphens only
    return f"s-{session_id[:36]}"


class VectorStore:
    """
    ChromaDB-backed vector store.
    One Chroma collection per research session.
    Embeddings are computed externally (BGE-M3) and passed in.
    """

    def _get_collection(self, session_id: str):
        return _get_client().get_or_create_collection(
            name=_collection_name(session_id),
            metadata={"hnsw:space": "cosine", "hnsw:construction_ef": 100},
        )

    async def add_chunks(self, session_id: str, chunks: List[dict]) -> int:
        """Embed and upsert chunks into ChromaDB."""
        if not chunks:
            return 0

        from app.services.embedding_service import embedding_service

        texts = [c["content"] for c in chunks]
        embeddings = await embedding_service.embed_texts(texts)

        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = []
        for c in chunks:
            meta = {
                "source_url": str(c.get("source_url", "")),
                "source_type": str(c.get("source_type", "web")),
                "credibility_score": float(c.get("credibility_score", 3.0)),
            }
            # Flatten any extra metadata — Chroma only accepts str/int/float/bool
            for k, v in (c.get("metadata") or {}).items():
                if isinstance(v, (str, int, float, bool)):
                    meta[k] = v
            metadatas.append(meta)

        collection = self._get_collection(session_id)
        loop = asyncio.get_event_loop()

        # Chroma's add() is synchronous — run in thread pool to not block event loop
        await loop.run_in_executor(
            None,
            lambda: collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            ),
        )

        log.info("chromadb_add_chunks", count=len(chunks), session_id=session_id)
        return len(chunks)

    async def hybrid_search(
        self,
        session_id: str,
        query: str,
        top_k: int = 10,
        alpha: float = 0.6,
    ) -> List[dict]:
        """
        Hybrid retrieval:
          1. Dense ANN via ChromaDB (cosine similarity with BGE-M3)
          2. BM25 keyword scoring over those candidates
          3. RRF score fusion (alpha blends dense vs keyword)
          4. Cross-encoder rerank
        """
        from app.services.embedding_service import embedding_service

        collection = self._get_collection(session_id)
        loop = asyncio.get_event_loop()

        count = await loop.run_in_executor(None, collection.count)
        if count == 0:
            log.warning("chromadb_empty_collection", session_id=session_id)
            return []

        n_results = min(top_k * 3, count)
        query_emb = await embedding_service.embed_query(query)

        raw = await loop.run_in_executor(
            None,
            lambda: collection.query(
                query_embeddings=[query_emb],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            ),
        )

        docs      = raw["documents"][0]
        metas     = raw["metadatas"][0]
        distances = raw["distances"][0]   # cosine distance: lower = more similar

        if not docs:
            return []

        candidates = [
            {
                "content":           doc,
                "source_url":        meta.get("source_url", ""),
                "source_type":       meta.get("source_type", "web"),
                "credibility_score": float(meta.get("credibility_score", 3.0)),
                "dense_score":       float(1.0 - dist),  # similarity
                "bm25_score":        0.0,
            }
            for doc, meta, dist in zip(docs, metas, distances)
        ]

        # BM25 over the dense candidate set
        corpus    = [c["content"].lower().split() for c in candidates]
        bm25      = BM25Okapi(corpus)
        bm25_raw  = bm25.get_scores(query.lower().split())
        bm25_max  = max(bm25_raw) if max(bm25_raw) > 0 else 1.0
        for c, s in zip(candidates, bm25_raw):
            c["bm25_score"] = float(s / bm25_max)

        # Score fusion
        for c in candidates:
            c["hybrid_score"] = alpha * c["dense_score"] + (1 - alpha) * c["bm25_score"]

        candidates.sort(key=lambda x: x["hybrid_score"], reverse=True)

        # Rerank top candidates
        reranked = await self._rerank(query, candidates[: top_k * 2])
        return reranked[:top_k]

    async def _rerank(self, query: str, candidates: List[dict]) -> List[dict]:
        """Cross-encoder reranker — falls back gracefully if model unavailable."""
        try:
            raise ImportError("offline mode")
            loop  = asyncio.get_event_loop()
            model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            pairs = [(query, c["content"][:512]) for c in candidates]
            scores = await loop.run_in_executor(
                None, lambda: model.predict(pairs).tolist()
            )
            for c, s in zip(candidates, scores):
                c["rerank_score"] = float(s)
            candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        except Exception as e:
            log.warning("reranker_fallback", error=str(e))
        return candidates

    async def delete_collection(self, session_id: str):
        """Remove a session's ChromaDB collection (cleanup)."""
        try:
            _get_client().delete_collection(_collection_name(session_id))
            log.info("chromadb_collection_deleted", session_id=session_id)
        except Exception as e:
            log.warning("chromadb_delete_failed", error=str(e))


# App-wide singleton — import this everywhere
vector_store = VectorStore()
