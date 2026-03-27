import json
import os
from datetime import datetime
from typing import Dict, List
from pathlib import Path

LOG_FILE = os.getenv("LOG_FILE", "logs/activity.log")

class ActivityLogger:
    def __init__(self):
        Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

    def _write(self, entry: Dict):
        entry["timestamp"] = datetime.utcnow().isoformat()
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def log_query(self, query: str, response: Dict, intermediate: Dict = None):
        self._write({
            "event": "query_completed",
            "query": query,
            "validation_score": response.get("validation_score"),
            "recommendation": response.get("recommendation"),
            "metrics": response.get("metrics"),
            "sources_count": len(response.get("sources", [])),
            "intermediate": intermediate or {}
        })

    def log_error(self, query: str, error: str):
        self._write({
            "event": "query_failed",
            "query": query,
            "error": error
        })

    def get_logs(self, limit: int = 50, event_type: str = None) -> List[Dict]:
        if not Path(LOG_FILE).exists():
            return []
        logs = []
        with open(LOG_FILE, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if event_type is None or entry.get("event") == event_type:
                        logs.append(entry)
                except json.JSONDecodeError:
                    continue
        return logs[-limit:]  # Most recent N entries

    def get_stats(self) -> Dict:
        logs = self.get_logs(limit=1000)
        completed = [l for l in logs if l["event"] == "query_completed"]
        failed    = [l for l in logs if l["event"] == "query_failed"]

        if not completed:
            return {"total_queries": 0, "failed": len(failed)}

        latencies = [l["metrics"]["latency_seconds"] for l in completed if l.get("metrics")]
        tokens    = [l["metrics"]["total_tokens"]    for l in completed if l.get("metrics")]
        costs     = [l["metrics"]["estimated_cost_usd"] for l in completed if l.get("metrics")]

        return {
            "total_queries": len(completed) + len(failed),
            "successful": len(completed),
            "failed": len(failed),
            "avg_latency_seconds": round(sum(latencies) / len(latencies), 3) if latencies else 0,
            "avg_tokens_per_query": int(sum(tokens) / len(tokens)) if tokens else 0,
            "total_cost_usd": round(sum(costs), 6),
            "avg_cost_per_query": round(sum(costs) / len(costs), 6) if costs else 0
        }
