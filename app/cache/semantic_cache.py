"""
app/cache/semantic_cache.py
─────────────────────────────────────────────────────────────────
STEP 14 — Semantic Query Cache ($0 Cost & Instant Latency)

WHAT:  Caches pipeline responses based on vector similarity of user queries.
WHY:   If a user asks a query semantically identical or very similar to a past query
       (e.g., "What is quantum computing?" vs "Explain quantum computing"),
       the system returns the cached response in <0.05s with $0 API cost!

STRATEGY:
  • Calculate embedding of incoming query.
  • Compute cosine similarity with cached query embeddings.
  • Threshold >= 0.90 triggers a CACHE HIT.
  • Persists cache data locally to ./cache/semantic_cache.json.
"""

import os
import json
import logging
import time
from typing import Optional, Tuple, Dict, Any, List
import numpy as np

from app.utils.embeddings import get_embedding

logger = logging.getLogger(__name__)

CACHE_FILE_PATH = os.getenv("CACHE_FILE_PATH", "./cache/semantic_cache.json")
SIMILARITY_THRESHOLD = float(os.getenv("CACHE_SIMILARITY_THRESHOLD", "0.85"))


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    v1 = np.array(vec1, dtype=float)
    v2 = np.array(vec2, dtype=float)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(v1, v2) / (norm1 * norm2))


class SemanticCache:
    """
    In-memory vector similarity cache with disk persistence.
    """

    def __init__(self, cache_file: str = CACHE_FILE_PATH, threshold: float = SIMILARITY_THRESHOLD):
        self.cache_file = cache_file
        self.threshold = threshold
        self.entries: List[Dict[str, Any]] = []
        self._load_cache()

    def _load_cache(self) -> None:
        """Load persistent cache entries from disk."""
        if not os.path.exists(self.cache_file):
            self.entries = []
            return

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                self.entries = json.load(f)
            logger.info(f"[SemanticCache] Loaded {len(self.entries)} entries from cache file.")
        except Exception as e:
            logger.error(f"[SemanticCache] Failed to load cache file: {e}")
            self.entries = []

    def _save_cache(self) -> None:
        """Persist cache entries to disk."""
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.entries, f, indent=2)
            logger.debug(f"[SemanticCache] Cache saved successfully ({len(self.entries)} entries).")
        except Exception as e:
            logger.error(f"[SemanticCache] Failed to save cache file: {e}")

    def get(self, query: str) -> Tuple[Optional[Dict[str, Any]], float]:
        """
        Check if query matches a cached entry by vector similarity.

        Returns:
            (cached_response_dict, highest_similarity_score)
        """
        if not self.entries:
            return None, 0.0

        try:
            query_emb = get_embedding(query)
        except Exception as e:
            logger.warning(f"[SemanticCache] Failed to embed query for cache check: {e}")
            return None, 0.0

        best_match = None
        highest_sim = 0.0

        for entry in self.entries:
            cached_emb = entry.get("embedding", [])
            if not cached_emb:
                continue

            sim = _cosine_similarity(query_emb, cached_emb)
            if sim > highest_sim:
                highest_sim = sim
                best_match = entry

        if highest_sim >= self.threshold and best_match is not None:
            logger.info(f"[SemanticCache] CACHE HIT! similarity={highest_sim:.4f} matched_query='{best_match.get('query')}'")
            cached_result = json.loads(json.dumps(best_match.get("result", {})))
            
            # Override metrics for cache hit response
            cached_result["cached"] = True
            cached_result["cache_similarity"] = round(highest_sim, 4)
            if "metrics" in cached_result:
                cached_result["metrics"]["total_latency_s"] = 0.03
                cached_result["metrics"]["estimated_cost_usd"] = 0.0
                cached_result["metrics"]["total_input_tokens"] = 0
                cached_result["metrics"]["total_output_tokens"] = 0
                cached_result["metrics"]["cache_hit"] = True
            return cached_result, highest_sim

        logger.debug(f"[SemanticCache] CACHE MISS. highest_sim={highest_sim:.4f}")
        return None, highest_sim

    def set(self, query: str, result: Dict[str, Any]) -> None:
        """
        Store query embedding and result in cache.
        """
        # Don't cache errored results or already cached results
        if result.get("error") or result.get("cached"):
            return

        try:
            query_emb = get_embedding(query)
            clean_res = json.loads(json.dumps(result))
            entry = {
                "query": query,
                "embedding": query_emb,
                "result": clean_res,
                "cached_at": time.time(),
            }
            self.entries.append(entry)
            self._save_cache()
            logger.info(f"[SemanticCache] Cached new result for query: '{query}'")
        except Exception as e:
            logger.error(f"[SemanticCache] Failed to store in cache: {e}")

    def clear(self) -> None:
        """Clear all cache entries."""
        self.entries = []
        if os.path.exists(self.cache_file):
            try:
                os.remove(self.cache_file)
            except Exception:
                pass


# Singleton cache instance
_cache_instance: Optional[SemanticCache] = None

def get_semantic_cache() -> SemanticCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SemanticCache()
    return _cache_instance
