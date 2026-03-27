"""
app/main.py
─────────────────────────────────────────────────────────────────
STEP 3 + 12 + 13 — FastAPI Application

WHAT:  The HTTP entry point. Exposes three endpoints:
         GET  /health  — liveness probe (load balancers call this)
         POST /ask     — the main research pipeline
         GET  /logs    — view monitoring logs with optional filters

WHY:   FastAPI gives us:
         • Automatic OpenAPI docs at /docs
         • Request validation via Pydantic (fail fast on bad input)
         • Async support for future scaling
         • Sub-millisecond router overhead

PRODUCTION TIP:
  Always add a /health endpoint.  Kubernetes, Docker, and load
  balancers use it.  Never tie health to LLM availability — return
  200 OK as long as the server process is alive.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

# ── Ensure project root is on Python path ─────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator import get_orchestrator
from app.monitoring.tracker import read_logs

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Startup / Shutdown ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up expensive resources (embeddings model, DB connection) on startup."""
    logger.info("🚀 Starting Autonomous Research Agent…")

    # Pre-initialize the orchestrator so first request is fast
    orchestrator = get_orchestrator()
    logger.info("✅ Orchestrator ready")

    yield  # ← server is running here

    logger.info("🛑 Shutting down Research Agent")


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Autonomous Research Agent",
    description=(
        "A multi-agent research system powered by Google Gemini and ChromaDB. "
        "Ask any question → get a researched, validated answer with metrics."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow browser clients (Postman, Swagger UI, React apps, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="The research question or topic to investigate",
        examples=["What is quantum computing?"],
    )

class ValidationDetail(BaseModel):
    overall_score: float
    relevance_score: float
    completeness_score: float
    accuracy_confidence: float
    is_acceptable: bool
    issues: list
    improvement_suggestions: str

class Metrics(BaseModel):
    total_latency_s: float
    step_latencies_s: dict
    total_input_tokens: int
    total_output_tokens: int
    estimated_cost_usd: float

class AskResponse(BaseModel):
    request_id: str
    answer: str
    sources: list
    validation_score: float
    validation: dict
    metrics: dict
    error: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    """
    Liveness probe.
    Always returns 200 OK if the server process is alive.
    """
    return {
        "status": "ok",
        "service": "autonomous-research-agent",
        "version": "1.0.0",
    }


@app.post("/ask", response_model=AskResponse, tags=["Research"])
async def ask(request: AskRequest):
    """
    **Main research endpoint.**

    Runs the full pipeline:
    1. Research Agent searches the web and stores in ChromaDB
    2. Summarizer Agent does RAG + Gemini generation
    3. Validator Agent scores the answer quality

    Returns the answer, sources, validation score, and performance metrics.
    """
    logger.info(f"[API] POST /ask | query='{request.query}'")

    try:
        orchestrator = get_orchestrator()
        result = orchestrator.run(query=request.query)
        return AskResponse(**result)

    except Exception as e:
        logger.error(f"[API] /ask failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs", tags=["Monitoring"])
async def get_logs(
    limit: int = Query(default=20, ge=1, le=200, description="Max number of logs to return"),
    query_filter: Optional[str] = Query(default=None, description="Filter logs by query text"),
    date_filter: Optional[str] = Query(
        default=None,
        description="Filter by date (YYYY-MM-DD format)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
):
    """
    **View monitoring logs.**

    Returns logged requests in reverse chronological order.
    Use `query_filter` and `date_filter` to narrow results.

    Example: GET /logs?limit=10&query_filter=quantum
    """
    logs = read_logs(limit=limit, query_filter=query_filter, date_filter=date_filter)
    return {
        "total": len(logs),
        "filters": {"query_filter": query_filter, "date_filter": date_filter},
        "logs": logs,
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Autonomous Research Agent API",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "POST /ask": "Submit a research query",
            "GET /logs": "View monitoring logs",
        },
    }


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", 8000))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
