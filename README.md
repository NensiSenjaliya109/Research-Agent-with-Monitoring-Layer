# 🤖 Autonomous Research Agent

A production-grade, multi-agent research system powered by **Google Gemini** and **ChromaDB**.

Submit a research query → get a sourced, validated answer with full performance metrics.

---

## 🏗️ Architecture

```
User Query (POST /ask)
        │
        ▼
  ┌─────────────┐
  │ Orchestrator│  ← sequences all stages
  └──────┬──────┘
         │
   ┌─────▼──────────────────────────────────┐
   │  Stage 1: Research Agent               │
   │  web_search(query) → raw snippets      │
   │  embed + store in ChromaDB             │
   └─────┬──────────────────────────────────┘
         │
   ┌─────▼──────────────────────────────────┐
   │  Stage 2: Summarizer Agent (RAG)       │
   │  retrieve relevant chunks from ChromaDB│
   │  inject as context → Gemini Flash      │
   │  generate grounded answer              │
   └─────┬──────────────────────────────────┘
         │
   ┌─────▼──────────────────────────────────┐
   │  Stage 3: Validator Agent              │
   │  LLM-as-Judge → scores answer 0–1     │
   └─────┬──────────────────────────────────┘
         │
   ┌─────▼──────────────────────────────────┐
   │  MonitoringTracker                     │
   │  latency / tokens / cost → logs/       │
   └────────────────────────────────────────┘
        │
        ▼
  Structured JSON Response
```

---

## 📁 Project Structure

```
research_agent/
├── app/
│   ├── main.py                  ← FastAPI endpoints
│   ├── agents/
│   │   ├── research_agent.py    ← Stage 1: search + store
│   │   ├── summarizer_agent.py  ← Stage 2: RAG + Gemini
│   │   └── validator_agent.py   ← Stage 3: quality scoring
│   ├── tools/
│   │   └── web_search.py        ← simulated/SerpAPI search
│   ├── vector_store/
│   │   └── chroma_store.py      ← ChromaDB wrapper
│   ├── monitoring/
│   │   └── tracker.py           ← latency/tokens/cost/logs
│   └── utils/
│       ├── gemini_client.py     ← Gemini API wrapper
│       └── embeddings.py        ← chunking + embedding
├── orchestrator.py              ← multi-agent coordinator
├── tests/
│   ├── test_gemini.py
│   ├── test_chromadb.py
│   ├── test_web_search.py
│   └── test_full_pipeline.py
├── logs/                        ← auto-created JSONL logs
├── chroma_db/                   ← auto-created vector DB
├── .env                         ← your API keys
└── requirements.txt
```

---

## ⚡ Quick Start

### 1. Create & activate virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API key

Edit `.env` and add your Gemini key:
```
GEMINI_API_KEY=your_key_here
```

> 🔑 **Get a FREE Gemini key** at https://aistudio.google.com/app/apikey
> Free tier: 15 RPM, 1M tokens/day — plenty for development.

### 4. Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for the interactive API explorer.

---

## 🧪 Testing

Run each test module from the `research_agent/` directory:

```bash
# Test Gemini API (requires GEMINI_API_KEY)
python tests/test_gemini.py

# Test ChromaDB + embeddings (no API key needed)
python tests/test_chromadb.py

# Test web search tool (no API key needed)
python tests/test_web_search.py

# End-to-end test (start server first!)
python tests/test_full_pipeline.py
```

---

## 🌐 API Reference

### `POST /ask`

```json
// Request
{ "query": "What is quantum computing?" }

// Response
{
  "request_id": "a3f2b1c0",
  "answer": "Quantum computing is...",
  "sources": ["search_result_1", "search_result_2"],
  "validation_score": 0.87,
  "validation": {
    "overall_score": 0.87,
    "relevance_score": 0.90,
    "completeness_score": 0.85,
    "accuracy_confidence": 0.85,
    "is_acceptable": true,
    "issues": [],
    "improvement_suggestions": "None"
  },
  "metrics": {
    "total_latency_s": 4.23,
    "step_latencies_s": {
      "web_search": 0.01,
      "embedding_and_storage": 1.12,
      "retrieval": 0.08,
      "llm_summarization": 2.45,
      "validation": 0.57
    },
    "total_input_tokens": 1842,
    "total_output_tokens": 387,
    "estimated_cost_usd": 0.00025
  }
}
```

### `GET /logs?limit=20&query_filter=quantum&date_filter=2024-01-01`

Returns monitoring logs (reverse chronological), filterable by query and date.

### `GET /health`

Liveness probe — always returns `{"status": "ok"}`.

---

## 🔧 Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Gemini API key from AI Studio |
| `SERPAPI_KEY` | *(empty)* | Optional — enables real web search |
| `EMBEDDING_BACKEND` | `sentence_transformers` | `gemini` or `sentence_transformers` |
| `GEMINI_LLM_MODEL` | `gemini-1.5-flash` | Gemini model name |
| `CHROMA_DB_PATH` | `./chroma_db` | ChromaDB storage directory |
| `LOG_FILE_PATH` | `./logs/agent_logs.json` | Monitoring log file |

---

## 🚀 Production Tips (Step 15)

### Reduce Latency
- Cache search results for repeated queries (Redis / in-memory dict)
- Run Research + Retrieval in parallel with `asyncio.gather()`
- Use `gemini-1.5-flash` over `pro` — 5× faster, 10× cheaper

### Reduce Cost
- Set `max_output_tokens` as low as acceptable per use case
- Batch embed multiple chunks in a single sentence-transformers call
- Skip validation for low-risk internal queries

### Scale
- FastAPI is already async-ready — add `async def` to run handlers concurrently
- Use a task queue (Celery + Redis) for long-running research jobs
- Deploy ChromaDB as a separate service for multi-instance setups

### Common Mistakes
| Mistake | Fix |
|---|---|
| No monitoring | Always log latency + tokens from day 1 |
| Too many LLM calls | Combine Research + Summary prompts when possible |
| Poor chunking | Test chunk size empirically — 400-600 chars is a good start |
| No error isolation | Wrap each agent in try/except, return partial results |
| Embedding mismatch | Use the same model to embed queries and documents |
