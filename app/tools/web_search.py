"""
tools/web_search.py
─────────────────────────────────────────────────────────────────
STEP 5 — Web Search Tool

WHAT:  Provides search_web(query) → List[str] of text snippets.
WHY:   The research agent needs fresh information beyond the LLM's
       training cutoff.  A tool decouples the agent from the API.

TWO MODES (chosen automatically):
  • REAL mode  : Uses SerpAPI when SERPAPI_KEY is set in .env
                 Free tier = 100 searches/month  (serpapi.com)
  • SIMULATED  : Returns realistic mock results when key is absent.
                 Perfect for development, demos, and learning.

PRODUCTION TIP:  Always implement a fallback.  If SerpAPI is down,
                 fall back to simulated data so the pipeline never
                 crashes completely.
"""

import os
import logging
from typing import List

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "").strip()


# ── Simulated Search Data ─────────────────────────────────────────────────────
# Realistic mock results keyed by topic keyword.
# In production, replace this entirely with a real API.
_MOCK_DATABASE = {
    "quantum computing": [
        "Quantum computing uses quantum mechanical phenomena like superposition and entanglement to process information. Unlike classical computers that store data as bits (0 or 1), quantum computers use qubits that can represent both states simultaneously.",
        "IBM and Google are leading the quantum computing race. Google's Sycamore processor achieved quantum supremacy in 2019, completing a task in 200 seconds that would take classical computers 10,000 years.",
        "Quantum algorithms like Shor's algorithm can factor large numbers exponentially faster than classical algorithms, posing a potential threat to current encryption standards like RSA.",
        "Quantum error correction is the biggest challenge in building practical quantum computers. Current qubits are highly sensitive to environmental noise, causing decoherence.",
        "Applications of quantum computing include drug discovery, financial modelling, logistics optimization, and breaking/creating cryptographic systems.",
    ],
    "machine learning": [
        "Machine learning is a subset of artificial intelligence where algorithms learn patterns from data without being explicitly programmed. It powers applications from email spam filters to self-driving cars.",
        "There are three main types of machine learning: supervised learning (learns from labeled data), unsupervised learning (finds hidden patterns), and reinforcement learning (learns through trial and error).",
        "Deep learning, a subset of ML, uses neural networks with multiple layers. It has revolutionized computer vision, natural language processing, and speech recognition.",
        "Overfitting occurs when a model memorizes training data but fails on new data. Techniques like dropout, regularization, and cross-validation help prevent it.",
        "The transformer architecture (introduced in 'Attention Is All You Need', 2017) powers modern LLMs like GPT and Gemini, enabling remarkable language understanding.",
    ],
    "climate change": [
        "Climate change refers to long-term shifts in global temperatures and weather patterns. Since the 1800s, human activities—primarily burning fossil fuels—have been the main driver.",
        "The IPCC 2023 report warns that without immediate action, global temperatures will exceed 1.5°C above pre-industrial levels by the early 2030s, causing severe weather events.",
        "Renewable energy (solar, wind, hydro) is now cheaper than fossil fuels in most markets. Solar capacity grew by 45% in 2023 alone, marking a major transition milestone.",
        "Carbon capture and storage (CCS) technology removes CO2 from the atmosphere. Iceland's Orca plant can capture 4,000 tonnes of CO2 per year, though scaling remains costly.",
        "Climate change disproportionately affects developing nations that contribute least to emissions, raising critical questions about climate justice and international responsibility.",
    ],
    "artificial intelligence": [
        "Artificial intelligence is the simulation of human intelligence by machines. Modern AI systems use large language models (LLMs), computer vision, and reinforcement learning.",
        "Large language models like GPT-4 and Gemini are trained on trillions of tokens of text. They exhibit emergent capabilities—skills that weren't explicitly taught during training.",
        "AI safety and alignment is a growing field focused on ensuring AI systems behave as intended. Concerns include misaligned objectives, bias amplification, and autonomous decision-making.",
        "Generative AI tools like image generators, code assistants, and chatbots generated over $20 billion in revenue in 2024, fundamentally transforming software development workflows.",
        "Agentic AI systems that can plan, use tools, and execute multi-step tasks are the next frontier. Companies like OpenAI, Google, and Anthropic are all racing to deploy autonomous agents.",
    ],
    "blockchain": [
        "Blockchain is a distributed ledger technology where transactions are recorded in immutable blocks chained together cryptographically. No single party controls the data.",
        "Bitcoin, created in 2009 by the pseudonymous Satoshi Nakamoto, was the first blockchain application. It uses proof-of-work consensus to validate transactions.",
        "Ethereum introduced smart contracts—self-executing code on the blockchain. This enabled DeFi (decentralized finance), NFTs, and DAOs to be built without intermediaries.",
        "Proof-of-stake (PoS) is a more energy-efficient consensus mechanism than proof-of-work. Ethereum's 2022 'Merge' reduced its energy consumption by ~99.95%.",
        "Enterprise blockchains like Hyperledger Fabric are used in supply chain, healthcare, and finance for transparent, auditable record-keeping without cryptocurrency.",
    ],
}

_DEFAULT_RESULTS = [
    "This is a rapidly evolving field with significant academic and commercial interest. Researchers worldwide are actively publishing new findings.",
    "Recent developments have accelerated progress in this domain, with major technology companies and universities leading research initiatives.",
    "Practical applications are emerging across multiple industries, demonstrating real-world impact and commercial viability.",
    "Key challenges include scalability, interpretability, and ethical considerations that the research community is actively addressing.",
    "Future directions suggest continued innovation with interdisciplinary approaches combining this field with adjacent technologies.",
]


def _simulated_search(query: str, num_results: int = 5) -> List[str]:
    """Return mock search results based on query keywords."""
    query_lower = query.lower()
    for keyword, results in _MOCK_DATABASE.items():
        if keyword in query_lower:
            logger.info(f"[SimSearch] matched topic: '{keyword}'")
            return results[:num_results]

    # Generic fallback for any topic not in our mock database
    logger.info(f"[SimSearch] no keyword match for '{query}', using defaults")
    return [f"Regarding '{query}': {r}" for r in _DEFAULT_RESULTS[:num_results]]


def _serpapi_search(query: str, num_results: int = 5) -> List[str]:
    """Perform real web search via SerpAPI."""
    params = {
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": num_results,
        "engine": "google",
    }
    try:
        response = requests.get(
            "https://serpapi.com/search",
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        # Extract organic search result snippets
        for item in data.get("organic_results", []):
            snippet = item.get("snippet", "")
            if snippet:
                results.append(snippet)

        logger.info(f"[SerpAPI] got {len(results)} results for '{query}'")
        return results[:num_results]

    except requests.exceptions.RequestException as e:
        logger.error(f"[SerpAPI] request failed: {e}. Falling back to simulated search.")
        return _simulated_search(query, num_results)


# ── Public Interface ──────────────────────────────────────────────────────────

def search_web(query: str, num_results: int = 5) -> List[str]:
    """
    Main tool: search_web(query) → List[str]

    Automatically selects real (SerpAPI) or simulated mode.
    Returns a list of text snippets — ready to feed into the research agent.
    """
    if SERPAPI_KEY:
        logger.info(f"[WebSearch] MODE=SerpAPI | query='{query}'")
        return _serpapi_search(query, num_results)
    else:
        logger.info(f"[WebSearch] MODE=Simulated | query='{query}'")
        return _simulated_search(query, num_results)


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    query = "What is quantum computing?"
    results = search_web(query)
    print(f"Query  : {query}")
    print(f"Results: {len(results)}")
    for i, r in enumerate(results, 1):
        print(f"\n[{i}] {r[:120]}…")
