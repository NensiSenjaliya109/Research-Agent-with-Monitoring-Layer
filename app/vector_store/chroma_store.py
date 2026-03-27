"""
vector_store/chroma_store.py
─────────────────────────────────────────────────────────────────
STEP 4 — ChromaDB Vector Store

WHAT:  Wraps ChromaDB to add, retrieve, and manage document vectors.
WHY:   Vector databases enable semantic search — finding documents
       by meaning, not just keyword matching.  This is the backbone
       of RAG (Retrieval-Augmented Generation).

PRODUCTION TIP:  Use a persistent directory (not in-memory) so your
                 knowledge base survives server restarts.  Always
                 pre-check for duplicate IDs before inserting.
"""

import os
import uuid
import logging
from typing import List, Optional

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
COLLECTION_NAME = "research_knowledge_base"


class ChromaStore:
    """
    Thread-safe ChromaDB wrapper.

    Exposes four operations the agent pipeline needs:
      add_documents  — store text chunks + their embeddings
      search         — find semantically similar chunks
      get_all        — dump the full collection (for debugging)
      clear          — wipe collection (use carefully!)
    """

    def __init__(self, collection_name: str = COLLECTION_NAME, db_path: str = CHROMA_DB_PATH):
        os.makedirs(db_path, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False),
        )

        # get_or_create is idempotent — safe to call on every startup
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},  # cosine similarity for text
        )
        logger.info(f"[ChromaDB] Collection '{collection_name}' ready. "
                    f"Docs: {self.collection.count()}")

    # ── Write ────────────────────────────────────────────────────────────────

    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Store text chunks with their pre-computed embeddings.

        Returns list of assigned document IDs.
        """
        if not texts:
            return []

        # Auto-generate UUIDs if IDs not provided
        doc_ids = ids or [str(uuid.uuid4()) for _ in texts]
        metas = metadatas or [{} for _ in texts]

        try:
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metas,
                ids=doc_ids,
            )
            logger.info(f"[ChromaDB] Added {len(texts)} chunks. Total: {self.collection.count()}")
            return doc_ids
        except Exception as e:
            logger.error(f"[ChromaDB] add_documents failed: {e}")
            raise

    # ── Read ─────────────────────────────────────────────────────────────────

    def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> List[dict]:
        """
        Find the top-N most similar documents to the query embedding.

        Returns list of dicts:
          [{"text": str, "id": str, "metadata": dict, "distance": float}, …]
        """
        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": min(n_results, self.collection.count() or 1),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = self.collection.query(**kwargs)

        output = []
        docs = results.get("documents", [[]])[0]
        ids = results.get("ids", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        for doc, doc_id, meta, dist in zip(docs, ids, metas, dists):
            output.append({
                "text": doc,
                "id": doc_id,
                "metadata": meta,
                "distance": round(dist, 4),
            })

        logger.debug(f"[ChromaDB] search returned {len(output)} results")
        return output

    def get_all(self) -> dict:
        """Return all stored documents (for debugging/inspection)."""
        return self.collection.get(include=["documents", "metadatas"])

    def count(self) -> int:
        return self.collection.count()

    def clear(self) -> None:
        """⚠️  Deletes ALL documents in the collection. Use with care."""
        self.client.delete_collection(COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.warning("[ChromaDB] Collection cleared.")


# ── Singleton accessor ────────────────────────────────────────────────────────
_store_instance: Optional[ChromaStore] = None

def get_store() -> ChromaStore:
    """Return a singleton ChromaStore (one DB connection per process)."""
    global _store_instance
    if _store_instance is None:
        _store_instance = ChromaStore()
    return _store_instance


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
    from app.utils.embeddings import get_embedding

    store = ChromaStore(collection_name="test_collection", db_path="./chroma_test")

    # Insert sample docs
    sample_texts = [
        "Python is a high-level programming language known for simplicity.",
        "FastAPI is a modern Python web framework for building APIs.",
        "ChromaDB is an open-source embedding database for AI applications.",
    ]
    embeddings = [get_embedding(t) for t in sample_texts]
    ids = store.add_documents(sample_texts, embeddings, [{"source": "test"}] * 3)
    print(f"Inserted {len(ids)} docs. Total in store: {store.count()}")

    # Similarity search
    query_emb = get_embedding("What web framework should I use for Python APIs?")
    results = store.search(query_emb, n_results=2)

    print("\n── Top matches ──")
    for r in results:
        print(f"  [{r['distance']:.4f}] {r['text']}")

    # Cleanup test collection
    store.clear()
    print("\n[ChromaDB] Test complete ✓")
