"""
utils/gemini_client.py
─────────────────────────────────────────────────────────────────
STEP 2 — Gemini API Client

WHAT:  A thin, reusable wrapper around Google's generativeai SDK.
WHY:   Centralising all Gemini calls means one place to update models,
       add retries, or swap providers without touching agent code.

PRODUCTION TIP:  Always wrap LLM calls with tenacity retry so transient
                 network errors never crash your pipeline.
"""

import os
import logging
from typing import Optional

import google.generativeai as genai
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
_API_KEY = os.getenv("GEMINI_API_KEY", "")
_LLM_MODEL = os.getenv("GEMINI_LLM_MODEL", "gemini-1.5-flash")
_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "models/text-embedding-004")

if not _API_KEY or _API_KEY == "your_gemini_api_key_here":
    logger.warning(
        "GEMINI_API_KEY is not set. Gemini calls will fail. "
        "Get a free key at https://aistudio.google.com/app/apikey"
    )
else:
    genai.configure(api_key=_API_KEY)


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
    Generate text using Gemini Flash.

    Returns a dict:
      {
        "text": str,          ← the generated answer
        "input_tokens": int,  ← estimated input token count
        "output_tokens": int, ← estimated output token count
      }
    """
    model_kwargs = {}
    if system_instruction:
        model_kwargs["system_instruction"] = system_instruction

    model = genai.GenerativeModel(
        model_name=_LLM_MODEL,
        generation_config=genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        ),
        **model_kwargs,
    )

    response = model.generate_content(prompt)
    text = response.text

    # Token estimation: Gemini SDK returns usage metadata when available
    try:
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
    except Exception:
        # Fallback: rough estimate (1 token ≈ 4 chars)
        input_tokens = len(prompt) // 4
        output_tokens = len(text) // 4

    logger.debug(f"[Gemini] in={input_tokens} out={output_tokens} model={_LLM_MODEL}")
    return {"text": text, "input_tokens": input_tokens, "output_tokens": output_tokens}


# ── Embeddings ────────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def get_embedding_gemini(text: str) -> list[float]:
    """
    Convert text → embedding vector using Gemini text-embedding-004.
    Dimension: 768 floats.
    """
    result = genai.embed_content(
        model=_EMBED_MODEL,
        content=text,
        task_type="retrieval_document",
    )
    return result["embedding"]


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    print("── Testing Gemini text generation ──")
    result = generate_text("In one sentence, what is machine learning?")
    print(f"Answer : {result['text'].strip()}")
    print(f"Tokens : input={result['input_tokens']}, output={result['output_tokens']}")

    print("\n── Testing Gemini embeddings ──")
    emb = get_embedding_gemini("Hello, world!")
    print(f"Embedding dim : {len(emb)}")
    print(f"First 5 values: {emb[:5]}")
