"""
utils/gemini_client.py
─────────────────────────────────────────────────────────────────
STEP 2 — Gemini API Client

WHAT:  A thin, reusable wrapper around Google's Gemini API.
WHY:   Centralising all Gemini calls means one place to update models,
       add retries, or swap providers without touching agent code.

PRODUCTION TIP: Always wrap LLM calls with tenacity retry so transient
                network errors don't crash the pipeline.
"""

import os
import logging
from typing import Optional

from google import genai
from google.genai import types
from dotenv import load_dotenv
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# ── Load environment variables ────────────────────────────────────────────────

load_dotenv()

# Prevent Google GenAI SDK from preferring global GOOGLE_API_KEY over local GEMINI_API_KEY
if "GEMINI_API_KEY" in os.environ and "GOOGLE_API_KEY" in os.environ:
    os.environ.pop("GOOGLE_API_KEY", None)

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

_API_KEY = os.getenv("GEMINI_API_KEY", "")

_LLM_MODEL = os.getenv(
    "GEMINI_LLM_MODEL",
    "gemini-2.5-flash",
)

_EMBED_MODEL = os.getenv(
    "GEMINI_EMBED_MODEL",
    "gemini-embedding-2",
)

# Keep 768 if your existing vector database/index expects 768 dimensions.
_EMBED_DIMENSION = int(
    os.getenv("GEMINI_EMBED_DIMENSION", "768")
)

# ── API Client ────────────────────────────────────────────────────────────────

if not _API_KEY or _API_KEY == "your_gemini_api_key_here":
    logger.warning(
        "GEMINI_API_KEY is not set. Gemini calls will fail. "
        "Get a key from Google AI Studio."
    )
    client = None
else:
    client = genai.Client(api_key=_API_KEY)


# ── LLM: Text Generation ──────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def generate_text(
    prompt: str,
    system_instruction: Optional[str] = None,
    temperature: float = 0.3,
    max_output_tokens: int = 2048,
) -> dict:
    """
    Generate text using Gemini.

    Returns:
        {
            "text": str,
            "input_tokens": int,
            "output_tokens": int,
        }
    """

    if client is None:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    config_kwargs = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }

    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction

    response = client.models.generate_content(
        model=_LLM_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            **config_kwargs
        ),
    )

    text = response.text or ""

    # Gemini returns usage metadata when available.
    try:
        input_tokens = (
            response.usage_metadata.prompt_token_count
        )
        output_tokens = (
            response.usage_metadata.candidates_token_count
        )
    except Exception:
        # Fallback estimation.
        input_tokens = len(prompt) // 4
        output_tokens = len(text) // 4

    logger.debug(
        "[Gemini] in=%s out=%s model=%s",
        input_tokens,
        output_tokens,
        _LLM_MODEL,
    )

    return {
        "text": text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


# ── Embeddings ────────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def get_embedding_gemini(text: str) -> list[float]:
    """
    Convert text → embedding vector using Gemini Embedding 2.

    The output dimensionality is configured to 768 so it remains
    compatible with an existing 768-dimensional vector index.
    """

    if client is None:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    result = client.models.embed_content(
        model=_EMBED_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=_EMBED_DIMENSION,
        ),
    )

    if not result.embeddings:
        raise RuntimeError(
            "Gemini returned no embedding."
        )

    embedding = result.embeddings[0].values

    if not embedding:
        raise RuntimeError(
            "Gemini returned an empty embedding."
        )

    logger.debug(
        "[Gemini] embedding_dim=%s model=%s",
        len(embedding),
        _EMBED_MODEL,
    )

    return list(embedding)


# ── Quick test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("── Testing Gemini text generation ──")

    result = generate_text(
        "In one sentence, what is machine learning?"
    )

    print(f"Answer : {result['text'].strip()}")
    print(
        f"Tokens : input={result['input_tokens']}, "
        f"output={result['output_tokens']}"
    )

    print("\n── Testing Gemini embeddings ──")

    emb = get_embedding_gemini(
        "Hello, world!"
    )

    print(f"Embedding dim : {len(emb)}")
    print(f"First 5 values: {emb[:5]}")