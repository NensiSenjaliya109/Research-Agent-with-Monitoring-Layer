from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
import asyncio
import uvicorn
import os
import sys

# Ensure the root directory 'research-agent' is in sys.path when running 'python app/main.py'
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.orchestrator import Orchestrator
from app.monitoring.logger import ActivityLogger

orchestrator = Orchestrator()
logger       = ActivityLogger()
executor     = ThreadPoolExecutor(max_workers=4)  # For running sync code in async

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Research Agent API starting...")
    yield
    print("🛑 Shutting down...")

app = FastAPI(
    title="Autonomous Research Agent",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class QueryRequest(BaseModel):
    query: str

class MetricsModel(BaseModel):
    latency_seconds: float
    total_tokens: int
    estimated_cost_usd: float
    breakdown: dict = {}

class ResearchResponse(BaseModel):
    answer: str
    sources: list[str]
    validation_score: float
    recommendation: str
    issues: list[str]
    metrics: MetricsModel


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

@app.post("/ask", response_model=ResearchResponse)
async def ask(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Run synchronous pipeline in thread pool to not block the event loop
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, orchestrator.run, request.query)
    return result

@app.get("/logs")
async def get_logs(limit: int = Query(default=50, le=500), event_type: str = None):
    logs = logger.get_logs(limit=limit, event_type=event_type)
    return {"logs": logs, "count": len(logs)}

@app.get("/stats")
async def get_stats():
    return logger.get_stats()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
