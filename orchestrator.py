"""
orchestrator.py
─────────────────────────────────────────────────────────────────
STEP 9 — Agent Orchestrator

WHAT:  The central controller that sequences all agents and tools.
       It is the ONLY component that knows the full pipeline flow.

WHY:   Orchestration is the core design pattern for multi-agent
       systems.  Each agent stays focused on ONE job (single
       responsibility), and the orchestrator wires them together.

PIPELINE FLOW:
  User Query
    ↓
  [ResearchAgent]   → search_web → embed → store in ChromaDB
    ↓
  [SummarizerAgent] → retrieve from ChromaDB → RAG prompt → Gemini
    ↓
  [ValidatorAgent]  → LLM-as-Judge → score the answer
    ↓
  Final structured response with metrics

PRODUCTION TIPS:
  • Log every step — when bugs appear, you need full traceability
  • Catch per-stage errors — a failing validator shouldn't kill the
    whole response.  Return partial results with error flags.
  • Add a cache layer before ResearchAgent for repeated queries.
"""

import logging

from app.agents.research_agent import ResearchAgent
from app.agents.summarizer_agent import SummarizerAgent
from app.agents.validator_agent import ValidatorAgent
from app.monitoring.tracker import MetricsTracker, log_request

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Coordinates the Research → Summarize → Validate pipeline.
    Returns a fully structured response ready for the API layer.
    """

    def __init__(self):
        self.research_agent = ResearchAgent(num_search_results=5)
        self.summarizer_agent = SummarizerAgent(n_retrieve=5)
        self.validator_agent = ValidatorAgent()

    def run(self, query: str) -> dict:
        """
        Run the full pipeline for a user query.

        Returns:
          {
            "answer"           : str,
            "sources"          : List[str],
            "validation"       : dict,
            "validation_score" : float,
            "metrics"          : dict,
            "request_id"       : str,
            "error"            : str | None,
          }
        """
        tracker = MetricsTracker(query=query)
        logger.info(f"[Orchestrator] === NEW REQUEST [{tracker.request_id}] === query='{query}'")

        answer = ""
        sources = []
        validation = {}
        error_msg = None

        try:
            # ── Stage 1: Research ────────────────────────────────────────────
            logger.info(f"[Orchestrator] Stage 1: Research")
            research_output = self.research_agent.run(query, tracker)
            sources = research_output.get("sources", [])

            logger.info(
                f"[Orchestrator] Research complete. "
                f"raw_results={len(research_output['raw_results'])}, "
                f"stored_chunks={research_output['stored_chunks']}"
            )

            # ── Stage 2: Summarize (RAG) ─────────────────────────────────────
            logger.info(f"[Orchestrator] Stage 2: RAG Summarization")
            summarizer_output = self.summarizer_agent.run(query, tracker)
            answer = summarizer_output.get("summary", "")

            logger.info(
                f"[Orchestrator] Summary complete. "
                f"length={len(answer)}, "
                f"chunks_used={len(summarizer_output.get('retrieved_chunks', []))}"
            )

            # ── Stage 3: Validate ─────────────────────────────────────────────
            logger.info(f"[Orchestrator] Stage 3: Validation")
            validation = self.validator_agent.run(query, answer, tracker)

            logger.info(
                f"[Orchestrator] Validation complete. "
                f"score={validation.get('overall_score', 0):.2f} "
                f"acceptable={validation.get('is_acceptable', True)}"
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[Orchestrator] Pipeline failed: {e}", exc_info=True)
            if not answer:
                answer = "An error occurred while processing your request. Please try again."

        # ── Build final response ──────────────────────────────────────────────
        record = tracker.to_dict(
            final_answer=answer,
            sources=sources,
            validation_score=validation.get("overall_score", 0.0),
            error=error_msg,
        )

        # Persist to log file (non-blocking — errors here won't crash the response)
        try:
            log_request(record)
        except Exception as log_err:
            logger.error(f"[Orchestrator] Log write failed: {log_err}")

        logger.info(
            f"[Orchestrator] === REQUEST COMPLETE [{tracker.request_id}] === "
            f"latency={tracker.total_latency}s "
            f"cost=${tracker.estimated_cost_usd:.6f}"
        )

        return {
            "request_id": tracker.request_id,
            "answer": answer,
            "sources": sources,
            "validation": validation,
            "validation_score": validation.get("overall_score", 0.0),
            "metrics": record["metrics"],
            "error": error_msg,
        }


# ── Singleton accessor (reuse agent instances across requests) ────────────────
_orchestrator: Orchestrator = None

def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
