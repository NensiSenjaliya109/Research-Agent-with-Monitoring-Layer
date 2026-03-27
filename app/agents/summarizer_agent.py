"""
agents/summarizer_agent.py
─────────────────────────────────────────────────────────────────
STEP 8b — Summarizer Agent (RAG-powered)

WHAT:  This agent performs RAG (Retrieval-Augmented Generation):
         1. Retrieves the most relevant chunks from ChromaDB
            using semantic search on the original query
         2. Injects those chunks as context into a Gemini prompt
         3. Returns a structured, grounded answer

WHY:   Without RAG, the LLM answers from training data alone
       (stale, hallucination-prone).  With RAG, the answer is
       anchored to the freshly retrieved evidence — much more
       reliable for production use.

PRODUCTION TIP:
  Always include the retrieved context verbatim in the prompt.
  Tell the model to cite sources.  This reduces hallucinations
  dramatically compared to asking the model to "rely on its knowledge".
"""

import logging

from app.vector_store.chroma_store import get_store
from app.utils.embeddings import get_embedding
from app.utils.gemini_client import generate_text
from app.monitoring.tracker import MetricsTracker

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert research assistant. Your task is to synthesize 
information from the provided context and generate a clear, accurate, and well-structured answer.

Rules:
- Base your answer ONLY on the provided context
- Be comprehensive but concise
- Use clear headings or bullet points if the answer is complex
- If the context does not fully answer the question, say so honestly
- Do not invent facts not present in the context"""

_SUMMARIZER_PROMPT = """Given the following research context, provide a comprehensive answer to the query.

QUERY: {query}

RETRIEVED CONTEXT:
{context}

Please provide a well-structured answer based on the above context."""


class SummarizerAgent:
    """
    Retrieves relevant knowledge from ChromaDB and generates
    a grounded answer using Gemini.
    """

    def __init__(self, n_retrieve: int = 5):
        self.n_retrieve = n_retrieve
        self.store = get_store()

    def run(self, query: str, tracker: MetricsTracker) -> dict:
        """
        Execute the RAG summarization pipeline.

        Returns:
          {
            "summary"          : str,         ← the generated answer
            "retrieved_chunks" : List[str],   ← context used
            "input_tokens"     : int,
            "output_tokens"    : int,
          }
        """
        logger.info(f"[SummarizerAgent] Running RAG for: '{query}'")

        # ── Step 1: Retrieve relevant chunks from ChromaDB ──────────────────
        tracker.start_step("retrieval")
        query_embedding = get_embedding(query)

        results = self.store.search(
            query_embedding=query_embedding,
            n_results=self.n_retrieve,
        )
        tracker.end_step("retrieval")

        retrieved_chunks = [r["text"] for r in results]
        logger.info(f"[SummarizerAgent] Retrieved {len(retrieved_chunks)} chunks")

        if not retrieved_chunks:
            logger.warning("[SummarizerAgent] No chunks retrieved — answering from LLM knowledge only")
            context = "No specific context available. Use your general knowledge."
        else:
            # Format context with numbering for clarity
            context = "\n\n".join(
                f"[{i+1}] {chunk}" for i, chunk in enumerate(retrieved_chunks)
            )

        # ── Step 2: Generate answer via Gemini ──────────────────────────────
        tracker.start_step("llm_summarization")
        prompt = _SUMMARIZER_PROMPT.format(query=query, context=context)

        gemini_response = generate_text(
            prompt=prompt,
            system_instruction=_SYSTEM_PROMPT,
            temperature=0.3,           # Lower = more factual, less creative
            max_output_tokens=1500,
        )
        tracker.end_step("llm_summarization")

        summary = gemini_response["text"]
        input_tokens = gemini_response["input_tokens"]
        output_tokens = gemini_response["output_tokens"]

        tracker.add_tokens(input_tokens, output_tokens)

        logger.info(
            f"[SummarizerAgent] Generated {len(summary)} chars, "
            f"tokens: in={input_tokens} out={output_tokens}"
        )

        return {
            "summary": summary,
            "retrieved_chunks": retrieved_chunks,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
