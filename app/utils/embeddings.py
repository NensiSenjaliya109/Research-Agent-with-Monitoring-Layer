"""
utils/embeddings.py
─────────────────────────────────────────────────────────────────
STEP 6 — Embeddings Pipeline

WHAT:  Converts raw text into numeric vectors and handles chunking.
WHY:   ChromaDB needs vectors, not raw text.  Good chunking is the
       #1 factor in RAG quality — too big = noise, too small = loss
       of context.

STRATEGY:
  • Chunk size : 500 characters  (~125 tokens, fits any model)
  • Overlap    : 50  characters  (prevents cutting mid-sentence)
  • Backend    : sentence-transformers by default (free, offline)
                 Switch to gemini in .env for production.
"""

import os
import logging
from typing import List

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "sentence_transformers").lower()
CHUNK_SIZE = 500        # characters
CHUNK_OVERLAP = 50      # characters


# ── Lazy-load the sentence-transformers model ─────────────────────────────────
_st_model = None

def _get_st_model():
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformers model (first call only)…")
        _st_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("sentence-transformers model loaded.")
    return _st_model


# ── Embeddings ────────────────────────────────────────────────────────────────

def get_embedding(text: str) -> List[float]:
    """
    Convert a single text string into an embedding vector.
    Selects backend based on EMBEDDING_BACKEND env var.
    """
    text = text.strip()
    if not text:
        raise ValueError("Cannot embed empty text.")

    if EMBEDDING_BACKEND == "gemini":
        from app.utils.gemini_client import get_embedding_gemini
        return get_embedding_gemini(text)
    else:
        model = _get_st_model()
        return model.encode(text, normalize_embeddings=True).tolist()


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of texts. Batch call is faster than looping.
    """
    texts = [t.strip() for t in texts if t.strip()]
    if EMBEDDING_BACKEND == "gemini":
        # Gemini has no batch endpoint — loop with rate-limit awareness
        return [get_embedding(t) for t in texts]
    else:
        model = _get_st_model()
        return model.encode(texts, normalize_embeddings=True).tolist()


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split long text into overlapping chunks.

    Production insight:
      Overlap ensures that facts spanning two chunks are not lost.
      A 10 % overlap is usually enough.  Increase for dense technical text.
    """
    text = text.strip()
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        # Move forward by (chunk_size - overlap) to create sliding window
        start += chunk_size - overlap

    return chunks


def embed_chunks(text: str) -> List[dict]:
    """
    Full pipeline: raw text → chunks → embeddings.

    Returns a list of dicts:
      [{"chunk": str, "embedding": List[float]}, …]
    """
    chunks = chunk_text(text)
    embeddings = get_embeddings_batch(chunks)
    return [{"chunk": c, "embedding": e} for c, e in zip(chunks, embeddings)]


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample = (
        "Quantum computing uses quantum mechanics to process information. "
        "Unlike classical bits (0 or 1), qubits can exist in superposition. "
        "This allows quantum computers to solve certain problems exponentially faster."
    )
    result = embed_chunks(sample)
    print(f"Chunks    : {len(result)}")
    print(f"Chunk[0]  : {result[0]['chunk'][:80]}…")
    print(f"Embed dim : {len(result[0]['embedding'])}")
    print("Embeddings pipeline OK ✓")
