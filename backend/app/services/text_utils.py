"""Shared text processing utilities — no cross-module imports."""
from typing import List

CREDIBILITY = {
    "sec_filing": 10, "official_website": 9, "crunchbase": 8,
    "news_tier1": 8,  "news": 8, "tavily": 7, "brave_search": 5,
    "linkedin": 7, "github": 6, "reddit": 3, "forum": 3,
    "unknown_blog": 1, "demo": 1,
}

def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> List[str]:
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunks.append(" ".join(words[i: i + chunk_size]))
        i += chunk_size - overlap
    return [c for c in chunks if len(c.strip()) > 50]
