import httpx
import os
import json
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

# ── Mock data — realistic enough to test the full pipeline ─────────
MOCK_RESULTS: Dict[str, List[Dict]] = {
    "default": [
        {
            "title": "Introduction to the topic",
            "url": "https://example.com/intro",
            "snippet": "This is a comprehensive overview covering the key concepts, history, and modern applications of the subject matter."
        },
        {
            "title": "Deep dive analysis",
            "url": "https://research.example.com/analysis",
            "snippet": "Researchers have found that the primary factors influencing outcomes include data quality, model architecture, and training methodology."
        },
        {
            "title": "Practical applications and case studies",
            "url": "https://casestudy.example.com",
            "snippet": "Real-world deployments have demonstrated 40% efficiency gains when applying these techniques in production environments."
        },
    ]
}


def _mock_search(query: str) -> List[Dict]:
    """
    Returns simulated search results.
    In production: replace with real API call below.
    """
    results = MOCK_RESULTS.get(query.lower(), MOCK_RESULTS["default"])
    # Inject the query into snippets to make them feel relevant
    enriched = []
    for r in results:
        enriched.append({
            "title": r["title"],
            "url": r["url"],
            "snippet": f"Regarding '{query}': {r['snippet']}"
        })
    return enriched


def _serpapi_search(query: str) -> List[Dict]:
    """
    Real web search via SerpAPI.
    Get free key at: https://serpapi.com (100 free searches/month)
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        raise ValueError("SERPAPI_KEY not set in .env")

    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": api_key,
        "num": 5,
        "engine": "google"
    }

    with httpx.Client(timeout=10.0) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    results = []
    for item in data.get("organic_results", [])[:5]:
        results.append({
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "snippet": item.get("snippet", "")
        })
    return results


def search_web(query: str, use_real_api: bool = False) -> List[Dict]:
    """
    Main search function used by the Research Agent.
    
    Args:
        query: The search query string
        use_real_api: Set True when SERPAPI_KEY is configured
    
    Returns:
        List of {"title", "url", "snippet"} dicts
    """
    try:
        if use_real_api and os.getenv("SERPAPI_KEY"):
            results = _serpapi_search(query)
        else:
            results = _mock_search(query)
        
        # Normalize output format regardless of source
        return [
            {
                "title": r.get("title", "Unknown"),
                "url": r.get("url", ""),
                "text": r.get("snippet", ""),  # unified key for downstream use
            }
            for r in results
        ]
    except Exception as e:
        print(f"⚠️ Search failed: {e} — returning empty results")
        return []


# ── Test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    results = search_web("artificial intelligence in healthcare")
    print(json.dumps(results, indent=2))
