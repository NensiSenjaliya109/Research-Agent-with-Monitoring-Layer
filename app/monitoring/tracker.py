"""
monitoring/tracker.py
─────────────────────────────────────────────────────────────────
STEP 11 — Monitoring System

WHAT:  Tracks latency, token usage, cost, and logs everything to
       a persistent JSON file.
WHY:   In production you MUST know:
         • How long each step takes (SLA monitoring)
         • How many tokens you consumed (cost control)
         • What failed and why (debugging)

DESIGN:
  • MetricsTracker — collects metrics for a single request
  • @track_step decorator — wraps any function to time it
  • log_request() — writes a complete request record to JSON log

COST MODEL (Gemini 1.5 Flash — as of 2024):
  Input  : $0.075 per 1M tokens
  Output : $0.30  per 1M tokens
"""

import os
import json
import time
import logging
import functools
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "./logs/agent_logs.json")

# Gemini 1.5 Flash pricing (USD per token)
COST_PER_INPUT_TOKEN = 0.075 / 1_000_000
COST_PER_OUTPUT_TOKEN = 0.30 / 1_000_000


# ── Metrics Container ─────────────────────────────────────────────────────────

class MetricsTracker:
    """
    Collects performance metrics for a single /ask request.
    Call start_step / end_step around each pipeline stage.
    Call to_dict() to serialize at the end.
    """

    def __init__(self, query: str):
        self.query = query
        self.request_id = _generate_id()
        self.start_time = time.perf_counter()
        self.step_latencies: dict[str, float] = {}
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self._step_start: Optional[float] = None
        self._current_step: Optional[str] = None

    # ── Step timing ──────────────────────────────────────────────────────────

    def start_step(self, step_name: str) -> None:
        self._current_step = step_name
        self._step_start = time.perf_counter()
        logger.debug(f"[Tracker] START step='{step_name}'")

    def end_step(self, step_name: Optional[str] = None) -> float:
        name = step_name or self._current_step or "unknown"
        elapsed = round(time.perf_counter() - (self._step_start or time.perf_counter()), 4)
        self.step_latencies[name] = elapsed
        logger.debug(f"[Tracker] END   step='{name}' latency={elapsed}s")
        return elapsed

    # ── Token tracking ───────────────────────────────────────────────────────

    def add_tokens(self, input_tokens: int, output_tokens: int) -> None:
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

    @property
    def estimated_cost_usd(self) -> float:
        return round(
            self.total_input_tokens * COST_PER_INPUT_TOKEN
            + self.total_output_tokens * COST_PER_OUTPUT_TOKEN,
            8,
        )

    @property
    def total_latency(self) -> float:
        return round(time.perf_counter() - self.start_time, 4)

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(
        self,
        final_answer: str = "",
        sources: list = None,
        validation_score: float = 0.0,
        error: Optional[str] = None,
    ) -> dict:
        return {
            "request_id": self.request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": self.query,
            "final_answer": final_answer,
            "sources": sources or [],
            "validation_score": validation_score,
            "metrics": {
                "total_latency_s": self.total_latency,
                "step_latencies_s": self.step_latencies,
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "estimated_cost_usd": self.estimated_cost_usd,
            },
            "error": error,
        }


# ── Decorator ─────────────────────────────────────────────────────────────────

def track_step(step_name: str):
    """
    @track_step("search")
    def my_function(tracker, ...):   ← tracker must be first arg
        ...

    Automatically calls tracker.start_step / end_step.
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(tracker: MetricsTracker, *args, **kwargs) -> Any:
            tracker.start_step(step_name)
            try:
                result = fn(tracker, *args, **kwargs)
                return result
            finally:
                tracker.end_step(step_name)
        return wrapper
    return decorator


# ── Log Persistence ───────────────────────────────────────────────────────────

def log_request(record: dict) -> None:
    """
    Append a request record to the JSON log file.

    Format: one JSON object per line (JSONL) — easy to parse and stream.
    """
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)

    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        logger.debug(f"[Monitor] Logged request_id={record.get('request_id')}")
    except Exception as e:
        logger.error(f"[Monitor] Failed to write log: {e}")


def read_logs(
    limit: int = 100,
    query_filter: Optional[str] = None,
    date_filter: Optional[str] = None,         # format: "YYYY-MM-DD"
) -> list[dict]:
    """
    Read logs from the JSONL file with optional filtering.
    Returns most recent records first.
    """
    if not os.path.exists(LOG_FILE_PATH):
        return []

    records = []
    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Apply filters
                if query_filter and query_filter.lower() not in rec.get("query", "").lower():
                    continue
                if date_filter and not rec.get("timestamp", "").startswith(date_filter):
                    continue

                records.append(rec)
    except Exception as e:
        logger.error(f"[Monitor] Failed to read logs: {e}")

    # Most recent first
    return list(reversed(records))[-limit:]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_id() -> str:
    import uuid
    return str(uuid.uuid4())[:8]


def estimate_tokens(text: str) -> int:
    """Quick token estimate: 1 token ≈ 4 characters."""
    return max(1, len(text) // 4)
