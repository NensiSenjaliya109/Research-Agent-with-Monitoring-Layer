from app.agents.research_agent import ResearchAgent
from app.agents.summarizer_agent import SummarizerAgent
from app.agents.validator_agent import ValidatorAgent
from app.monitoring.logger import ActivityLogger
from app.utils.text_processor import calculate_cost
from typing import Dict
import time

logger = ActivityLogger()

class Orchestrator:
    """
    Controls the full agent pipeline.
    
    Flow:
    User Query
      → Research Agent (fetch + store)
      → Summarizer Agent (condense)
      → Validator Agent (score + finalize)
      → Structured Response
    """

    def __init__(self):
        self.research_agent   = ResearchAgent()
        self.summarizer_agent = SummarizerAgent()
        self.validator_agent  = ValidatorAgent()

    def run(self, query: str) -> Dict:
        pipeline_start = time.time()
        total_tokens   = 0
        total_cost     = 0.0
        
        print(f"\n{'='*50}")
        print(f"🤖 Orchestrator: Processing query: '{query}'")
        print(f"{'='*50}")

        # ── STEP 1: Research ────────────────────────────────────
        research_result = self.research_agent.run(query)
        
        if research_result["status"] == "no_results":
            return self._error_response(query, "No search results found", pipeline_start)

        # ── STEP 2: Summarize ───────────────────────────────────
        summary_result = self.summarizer_agent.run(
            query=query,
            raw_text=research_result["raw_text"]
        )
        total_tokens += summary_result["input_tokens"] + summary_result["output_tokens"]
        total_cost   += summary_result["cost"]

        # ── STEP 3: Validate ────────────────────────────────────
        validation_result = self.validator_agent.run(
            query=query,
            summary=summary_result["summary"],
            sources=research_result["sources"]
        )
        total_tokens += validation_result["input_tokens"] + validation_result["output_tokens"]
        total_cost   += validation_result["cost"]

        total_latency = round(time.time() - pipeline_start, 3)

        # ── Assemble Final Response ─────────────────────────────
        response = {
            "answer": validation_result.get("final_answer", summary_result["summary"]),
            "sources": research_result["sources"],
            "validation_score": validation_result.get("overall_score", 0.0),
            "recommendation": validation_result.get("recommendation", "PASS"),
            "issues": validation_result.get("issues", []),
            "metrics": {
                "latency_seconds": total_latency,
                "total_tokens": total_tokens,
                "estimated_cost_usd": round(total_cost, 6),
                "breakdown": {
                    "research_latency": research_result["latency"],
                    "summarizer_latency": summary_result["latency"],
                    "validator_latency": validation_result["latency"],
                    "chunks_stored": research_result["chunks_stored"]
                }
            }
        }

        # ── Log the full activity ───────────────────────────────
        logger.log_query(
            query=query,
            response=response,
            intermediate={
                "research_status": research_result["status"],
                "summary_snippet": summary_result["summary"][:200],
                "validation_issues": validation_result.get("issues", [])
            }
        )

        print(f"\n✅ Pipeline complete | {total_latency}s | {total_tokens} tokens | ${total_cost:.6f}")
        return response

    def _error_response(self, query: str, error: str, start_time: float) -> Dict:
        latency = round(time.time() - start_time, 3)
        logger.log_error(query=query, error=error)
        return {
            "answer": f"Could not find information about: {query}",
            "sources": [],
            "validation_score": 0.0,
            "recommendation": "FAIL",
            "issues": [error],
            "metrics": {
                "latency_seconds": latency,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
                "breakdown": {}
            }
        }
