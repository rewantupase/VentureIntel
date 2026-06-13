"""
Embedding service — offline-safe implementation.
Uses a deterministic hash-based sparse embedding that works without any
network access or model downloads. In production swap this for BGE-M3 or
the ChromaDB ONNX model once network/GPU is available.

Dim: 384 (matches MiniLM slot in ChromaDB).
"""
import asyncio
import hashlib
import numpy as np
import structlog
from typing import List

log = structlog.get_logger()

EMBEDDING_DIM = 384


def _hash_embed(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """
    Deterministic sparse embedding via seeded random projection.
    Same text → same vector. Cosine similarity works correctly.
    """
    seed = int(hashlib.md5(text.lower().encode()).hexdigest(), 16) % (2**32)
    rng = np.random.default_rng(seed)

    # Project each word into the embedding space and sum
    words = text.lower().split()
    vec = np.zeros(dim, dtype=np.float32)
    for word in words:
        ws = int(hashlib.md5(word.encode()).hexdigest(), 16) % (2**32)
        wrng = np.random.default_rng(ws)
        vec += wrng.standard_normal(dim).astype(np.float32)

    # Normalize to unit vector
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    else:
        vec = rng.standard_normal(dim).astype(np.float32)
        vec /= np.linalg.norm(vec)

    return vec.tolist()


class EmbeddingService:
    def __init__(self):
        self.dim = EMBEDDING_DIM
        log.info("embedding_service_ready", mode="offline_hash", dim=self.dim)

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._batch, texts)

    def _batch(self, texts: List[str]) -> List[List[float]]:
        return [_hash_embed(t) for t in texts]

    async def embed_query(self, query: str) -> List[float]:
        return _hash_embed(query)


embedding_service = EmbeddingService()
