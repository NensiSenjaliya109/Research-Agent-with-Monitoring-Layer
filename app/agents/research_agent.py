"""
agents/research_agent.py
─────────────────────────────────────────────────────────────────
STEP 8a — Research Agent

WHAT:  The first agent in the pipeline. It:
         1. Calls the web search tool to collect raw information
         2. Stores the results in ChromaDB for later retrieval
         3. Returns the raw text snippets to the orchestrator

WHY:   Separation of concerns — this agent ONLY focuses on
       information gathering.  It does not summarize or judge.
       In production you might run N research agents in parallel
       for different sub-queries — search-and-store is parallelisable.

PRODUCTION TIP:
  Add source metadata (URL, timestamp) to every chunk so users
  can verify answers.  Traceability is critical in production RAG.
"""

import logging
from typing import List

from app.tools.web_search import search_web
from app.vector_store.chroma_store import get_store
from app.utils.embeddings import embed_chunks
from app.monitoring.tracker import MetricsTracker

logger = logging.getLogger(__name__)


class ResearchAgent:
    """
    Collects information on a topic by:
      1. Searching the web
      2. Chunking and embedding each result
      3. Storing everything in ChromaDB
    """

    def __init__(self, num_search_results: int = 5):
        self.num_search_results = num_search_results
        self.store = get_store()

    def run(self, query: str, tracker: MetricsTracker) -> dict:
        """
        Execute the research pipeline.

        Returns:
          {
            "raw_results"  : List[str],   ← raw snippets from search
            "stored_chunks": int,          ← number of chunks stored in DB
            "sources"      : List[str],    ← source labels for provenance
          }
        """
        logger.info(f"[ResearchAgent] Starting research for: '{query}'")

        # ── Step 1: Web search ──────────────────────────────────────────────
        tracker.start_step("web_search")
        raw_results: List[str] = search_web(query, num_results=self.num_search_results)
        tracker.end_step("web_search")

        if not raw_results:
            logger.warning("[ResearchAgent] No results returned from search")
            return {"raw_results": [], "stored_chunks": 0, "sources": []}

        logger.info(f"[ResearchAgent] Retrieved {len(raw_results)} search results")

        # ── Step 2: Chunk + embed + store in ChromaDB ───────────────────────
        tracker.start_step("embedding_and_storage")
        all_chunks = []
        all_embeddings = []
        all_metadatas = []

        for i, result_text in enumerate(raw_results):
            # embed_chunks handles chunking + embedding in one call
            chunk_data = embed_chunks(result_text)

            for j, item in enumerate(chunk_data):
                all_chunks.append(item["chunk"])
                all_embeddings.append(item["embedding"])
                all_metadatas.append({
                    "source": f"search_result_{i+1}",
                    "query": query,
                    "chunk_index": j,
                })

        stored_ids = self.store.add_documents(
            texts=all_chunks,
            embeddings=all_embeddings,
            metadatas=all_metadatas,
        )
        tracker.end_step("embedding_and_storage")

        logger.info(
            f"[ResearchAgent] Stored {len(stored_ids)} chunks in ChromaDB "
            f"({len(raw_results)} results → {len(all_chunks)} chunks)"
        )

        return {
            "raw_results": raw_results,
            "stored_chunks": len(stored_ids),
            "sources": [m["source"] for m in all_metadatas[:self.num_search_results]],
        }
