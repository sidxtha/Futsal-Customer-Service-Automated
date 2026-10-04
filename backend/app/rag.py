"""Embeddings + retrieval over the kb_chunks table."""
import math
import os
import time

from google.genai import types

from .classifier import client, _is_transient

EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
EMBED_DIM = 768  # must match vector(768) in schema.sql


def _normalize(v: list[float]) -> list[float]:
    # Gemini only pre-normalizes the full 3072-dim output; smaller sizes must be normalized.
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def embed(text: str, task_type: str, retries: int = 3) -> list[float]:
    """task_type: 'RETRIEVAL_DOCUMENT' when ingesting, 'RETRIEVAL_QUERY' when searching."""
    delay = 1.0
    for attempt in range(retries):
        try:
            resp = client.models.embed_content(
                model=EMBED_MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type=task_type, output_dimensionality=EMBED_DIM
                ),
            )
            return _normalize(list(resp.embeddings[0].values))
        except Exception as e:
            if not _is_transient(e) or attempt == retries - 1:
                raise
            time.sleep(delay)
            delay *= 2


def search(db, query: str, k: int = 4) -> list[dict]:
    """Returns [{id, source, content, similarity}], best first. similarity is cosine (1 = identical)."""
    qv = embed(query, "RETRIEVAL_QUERY")
    res = db.rpc("match_kb_chunks", {"query_embedding": qv, "match_count": k}).execute()
    return res.data or []