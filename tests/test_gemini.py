"""
tests/test_gemini.py — STEP 14a
Test the Gemini API client in isolation.
Run: python tests/test_gemini.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.utils.gemini_client import generate_text, get_embedding_gemini

def test_text_generation():
    print("\n── Test 1: Text Generation ──────────────────────────")
    result = generate_text("In exactly one sentence, what is machine learning?")
    assert isinstance(result["text"], str) and len(result["text"]) > 10, "Empty response!"
    assert result["input_tokens"] > 0
    assert result["output_tokens"] > 0
    print(f"  Answer : {result['text'].strip()}")
    print(f"  Tokens : in={result['input_tokens']} out={result['output_tokens']}")
    print("  ✅ PASS")

def test_embeddings():
    print("\n── Test 2: Embeddings ───────────────────────────────")
    emb = get_embedding_gemini("Hello, world!")
    assert isinstance(emb, list) and len(emb) == 768, f"Expected 768-dim, got {len(emb)}"
    print(f"  Dimension : {len(emb)}")
    print(f"  Sample    : {emb[:3]}")
    print("  ✅ PASS")

if __name__ == "__main__":
    print("=" * 55)
    print(" Gemini API Tests")
    print("=" * 55)
    try:
        test_text_generation()
        test_embeddings()
        print("\n✅ All Gemini tests passed!")
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        print("  → Check GEMINI_API_KEY in .env")
        sys.exit(1)
