"""
tests/test_web_search.py — STEP 14c
Test the web search tool (simulated + optional SerpAPI).
Run: python tests/test_web_search.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.tools.web_search import search_web

def test_known_topic():
    print("\n── Test 1: Known topic search ───────────────────────")
    results = search_web("quantum computing", num_results=3)
    print(f"  Results  : {len(results)}")
    for i, r in enumerate(results, 1):
        print(f"  [{i}] {r[:100]}…")
    assert len(results) == 3
    assert all(isinstance(r, str) and len(r) > 20 for r in results)
    print("  ✅ PASS")

def test_unknown_topic():
    print("\n── Test 2: Unknown topic (generic fallback) ─────────")
    results = search_web("xylophone manufacturing history", num_results=3)
    print(f"  Results  : {len(results)}")
    assert len(results) == 3
    assert all(isinstance(r, str) for r in results)
    print("  ✅ PASS")

def test_all_topics():
    print("\n── Test 3: All mock topics ──────────────────────────")
    topics = ["machine learning", "climate change", "artificial intelligence", "blockchain"]
    for topic in topics:
        r = search_web(topic, num_results=2)
        assert len(r) == 2, f"Failed for topic: {topic}"
        print(f"  '{topic}' → {len(r)} results ✓")
    print("  ✅ PASS")

if __name__ == "__main__":
    print("=" * 55)
    print(" Web Search Tool Tests")
    print("=" * 55)
    try:
        test_known_topic()
        test_unknown_topic()
        test_all_topics()
        print("\n✅ All web search tests passed!")
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
