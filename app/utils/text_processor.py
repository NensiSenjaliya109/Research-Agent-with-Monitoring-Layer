import re
from typing import List

def clean_text(text: str) -> str:
    """Remove noise from scraped web text."""
    text = re.sub(r'\s+', ' ', text)         # collapse whitespace
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # remove non-ASCII
    text = text.strip()
    return text

def estimate_tokens(text: str) -> int:
    """
    Fast token estimator without loading tiktoken.
    Rule of thumb: 1 token ≈ 4 chars in English.
    Accurate to within ~10% for Gemini.
    """
    return len(text) // 4

def format_search_results(results: List[dict]) -> str:
    """
    Convert raw search results into a single string for embedding/prompting.
    """
    parts = []
    for i, r in enumerate(results, 1):
        parts.append(f"[Source {i}] {r['title']}\nURL: {r['url']}\n{r['text']}")
    return "\n\n---\n\n".join(parts)

def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """
    Gemini 1.5 Flash pricing (as of mid-2024):
    Input:  $0.075 per 1M tokens (≤128k context)
    Output: $0.30  per 1M tokens
    Update this when Google changes pricing.
    """
    input_cost  = (input_tokens  / 1_000_000) * 0.075
    output_cost = (output_tokens / 1_000_000) * 0.30
    return round(input_cost + output_cost, 8)
