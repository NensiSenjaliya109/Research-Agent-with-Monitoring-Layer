"""
tests/test_full_pipeline.py — STEP 14d
End-to-end test: calls the running FastAPI server.
REQUIRES: Server running at http://localhost:8000

Run:
  Terminal 1: uvicorn app.main:app --reload --port 8000
  Terminal 2: python tests/test_full_pipeline.py
"""
import sys
import json
import time

try:
    import requests
except ImportError:
    print("❌ 'requests' not installed. Run: pip install requests")
    sys.exit(1)

BASE_URL = "http://localhost:8000"


def test_health():
    print("\n── Test 1: Health endpoint ──────────────────────────")
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert data["status"] == "ok"
    print(f"  Status   : {data['status']}")
    print(f"  Version  : {data['version']}")
    print("  ✅ PASS")


def test_ask_endpoint():
    print("\n── Test 2: POST /ask ────────────────────────────────")
    payload = {"query": "What is quantum computing and how does it work?"}

    start = time.time()
    r = requests.post(f"{BASE_URL}/ask", json=payload, timeout=60)
    elapsed = round(time.time() - start, 2)

    print(f"  HTTP Status : {r.status_code}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}\n{r.text}"

    data = r.json()
    print(f"  Request ID  : {data['request_id']}")
    print(f"  Answer len  : {len(data['answer'])} chars")
    print(f"  Sources     : {data['sources']}")
    print(f"  Val. Score  : {data['validation_score']:.2f}")
    print(f"  Latency     : {data['metrics']['total_latency_s']}s")
    print(f"  Tokens      : in={data['metrics']['total_input_tokens']} out={data['metrics']['total_output_tokens']}")
    print(f"  Cost (est.) : ${data['metrics']['estimated_cost_usd']:.6f}")
    print(f"  Round-trip  : {elapsed}s")

    assert len(data["answer"]) > 50, "Answer too short"
    assert 0.0 <= data["validation_score"] <= 1.0
    assert "total_latency_s" in data["metrics"]
    print("  ✅ PASS")
    return data


def test_logs_endpoint():
    print("\n── Test 3: GET /logs ────────────────────────────────")
    r = requests.get(f"{BASE_URL}/logs?limit=5", timeout=5)
    assert r.status_code == 200
    data = r.json()
    print(f"  Total logs  : {data['total']}")
    if data["logs"]:
        last = data["logs"][0]
        print(f"  Last query  : {last['query']}")
        print(f"  Timestamp   : {last['timestamp']}")
    print("  ✅ PASS")


def test_invalid_query():
    print("\n── Test 4: Invalid (too short) query ────────────────")
    r = requests.post(f"{BASE_URL}/ask", json={"query": "hi"}, timeout=5)
    print(f"  HTTP Status : {r.status_code}")
    assert r.status_code == 422, f"Expected 422 validation error, got {r.status_code}"
    print("  ✅ PASS — properly rejected by Pydantic validation")


def test_ml_query():
    print("\n── Test 5: Machine learning query ───────────────────")
    r = requests.post(
        f"{BASE_URL}/ask",
        json={"query": "Explain machine learning types with examples"},
        timeout=60,
    )
    assert r.status_code == 200
    data = r.json()
    print(f"  Answer preview: {data['answer'][:150]}…")
    print(f"  Val. Score    : {data['validation_score']:.2f}")
    print("  ✅ PASS")


if __name__ == "__main__":
    print("=" * 55)
    print(" Full Pipeline Integration Tests")
    print(" (Server must be running at localhost:8000)")
    print("=" * 55)

    # Check server is up before running tests
    try:
        requests.get(f"{BASE_URL}/health", timeout=3)
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to {BASE_URL}")
        print("   Start the server first:")
        print("   uvicorn app.main:app --reload --port 8000")
        sys.exit(1)

    try:
        test_health()
        test_ask_endpoint()
        test_logs_endpoint()
        test_invalid_query()
        test_ml_query()
        print("\n" + "=" * 55)
        print("✅ All integration tests passed!")
        print("=" * 55)
    except AssertionError as e:
        print(f"\n❌ Assertion FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
