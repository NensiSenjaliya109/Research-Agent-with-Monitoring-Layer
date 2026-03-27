"""
tests/test_chromadb.py — STEP 14b
Test ChromaDB insert and similarity search.
Run: python tests/test_chromadb.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.vector_store.chroma_store import ChromaStore
from app.utils.embeddings import get_embedding

TEST_COLLECTION = "test_chromadb_run"
TEST_DB_PATH = "./chroma_test_temp"

def test_insert_and_search():
    print("\n── Test 1: Insert + Search ──────────────────────────")
    store = ChromaStore(collection_name=TEST_COLLECTION, db_path=TEST_DB_PATH)
    store.clear()  # start fresh

    texts = [
        "Python is a high-level programming language known for readability.",
        "FastAPI is a modern web framework for Python APIs.",
        "ChromaDB is a vector database for AI applications.",
        "Machine learning is a subset of artificial intelligence.",
        "Neural networks are inspired by the human brain.",
    ]
    embeddings = [get_embedding(t) for t in texts]
    ids = store.add_documents(texts, embeddings, [{"source": "test"}] * len(texts))

    print(f"  Inserted : {len(ids)} docs")
    assert store.count() == len(texts), f"Expected {len(texts)}, got {store.count()}"
    print(f"  Count    : {store.count()}")

    # Semantic search
    query_emb = get_embedding("Which Python library should I use for APIs?")
    results = store.search(query_emb, n_results=2)

    print(f"  Results  : {len(results)}")
    print(f"  Top match: {results[0]['text'][:80]}…")
    print(f"  Distance : {results[0]['distance']}")

    assert len(results) > 0
    assert results[0]["distance"] < 0.5, "Top result should be semantically close"
    print("  ✅ PASS")

    store.clear()
    print("  (Test collection cleaned up)")

def test_empty_search():
    print("\n── Test 2: Search on Empty Collection ───────────────")
    store = ChromaStore(collection_name=TEST_COLLECTION + "_empty", db_path=TEST_DB_PATH)
    store.clear()
    count = store.count()
    assert count == 0
    print(f"  Count: {count}")
    print("  ✅ PASS")
    store.clear()

if __name__ == "__main__":
    print("=" * 55)
    print(" ChromaDB Tests")
    print("=" * 55)
    try:
        test_insert_and_search()
        test_empty_search()
        print("\n✅ All ChromaDB tests passed!")
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
