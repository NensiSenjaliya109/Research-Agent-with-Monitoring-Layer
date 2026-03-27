import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import hashlib
import os

# Using sentence-transformers as free local embeddings
# Swap to Gemini Embeddings API if you need higher quality
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # Fast, 384-dim, great for retrieval

class ChromaStore:
    def __init__(self, persist_dir: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="research_knowledge",
            metadata={"hnsw:space": "cosine"}  # Cosine similarity for text
        )
        self.encoder = SentenceTransformer(EMBEDDING_MODEL)
        print(f"✅ ChromaDB initialized | Collection docs: {self.collection.count()}")

    def _make_id(self, text: str) -> str:
        """Stable ID based on content hash — prevents duplicate insertions."""
        return hashlib.md5(text.encode()).hexdigest()

    def chunk_text(self, text: str, chunk_size: int = 400, overlap: int = 80) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Why overlap? So context at chunk boundaries isn't lost.
        Chunk size 400 words ≈ 500-600 tokens — safe for most LLMs.
        """
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            start += (chunk_size - overlap)   # slide with overlap
        return chunks

    def add_documents(self, texts: List[str], metadatas: List[Dict] = None) -> int:
        """
        Chunk, embed, and store documents.
        Returns total chunks stored.
        """
        all_chunks, all_ids, all_metas = [], [], []

        for i, text in enumerate(texts):
            chunks = self.chunk_text(text)
            for j, chunk in enumerate(chunks):
                chunk_id = self._make_id(chunk)
                meta = (metadatas[i] if metadatas else {})
                meta["chunk_index"] = j
                all_chunks.append(chunk)
                all_ids.append(chunk_id)
                all_metas.append(meta)

        if not all_chunks:
            return 0

        embeddings = self.encoder.encode(all_chunks).tolist()

        # ChromaDB handles duplicates via IDs — safe to re-insert
        self.collection.upsert(
            documents=all_chunks,
            embeddings=embeddings,
            ids=all_ids,
            metadatas=all_metas
        )
        return len(all_chunks)

    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        Semantic search — returns top-N relevant chunks.
        """
        query_embedding = self.encoder.encode([query]).tolist()
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=min(n_results, self.collection.count() or 1),
            include=["documents", "metadatas", "distances"]
        )

        output = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            output.append({
                "text": doc,
                "metadata": meta,
                "relevance_score": round(1 - dist, 4)  # cosine: 1=identical
            })
        return output

    def clear(self):
        """Wipe the collection — useful for testing."""
        self.client.delete_collection("research_knowledge")
        self.collection = self.client.get_or_create_collection(
            name="research_knowledge",
            metadata={"hnsw:space": "cosine"}
        )


# ── Quick test ─────────────────────────────────────────────────────
if __name__ == "__main__":
    store = ChromaStore()

    docs = [
        "Python is a high-level programming language known for its simplicity.",
        "FastAPI is a modern web framework for building APIs with Python.",
        "ChromaDB is an open-source vector database used for AI applications.",
        "Machine learning models learn patterns from training data.",
    ]
    
    n = store.add_documents(docs, metadatas=[{"source": "test"}] * len(docs))
    print(f"Stored {n} chunks")

    results = store.search("What is a vector database for AI?")
    for r in results:
        print(f"[{r['relevance_score']}] {r['text'][:80]}...")
