# 🤖 Autonomous Research Agent with Monitoring System

> A production-grade, multi-agent AI research system that searches the web, processes information, stores knowledge in a vector database, and returns validated, structured answers — powered by Google Gemini and FastAPI.

---

## 📋 Table of Contents

- [What Is This?](#-what-is-this)
- [How It Works](#-how-it-works)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Project Structure](#-project-structure)
- [Installation & Setup](#-installation--setup)
- [Configuration](#-configuration)
- [Running the Server](#-running-the-server)
- [API Endpoints](#-api-endpoints)
- [Testing the System](#-testing-the-system)
- [Example Queries & Responses](#-example-queries--responses)
- [Real-World Use Cases](#-real-world-use-cases)
- [Monitoring & Logs](#-monitoring--logs)
- [Cost Estimation](#-cost-estimation)
- [Troubleshooting](#-troubleshooting)
- [Production Tips](#-production-tips)

---

## 🧠 What Is This?

The **Autonomous Research Agent** is a backend AI system that takes any question or topic from a user, autonomously researches it using web search, processes and stores the findings in a vector database, and returns a clean, validated answer — along with sources, quality scores, and performance metrics.

Think of it as your personal AI research assistant exposed as a REST API.

**What makes it different from just calling ChatGPT:**
- It actively searches the web for fresh information (not just training data)
- Multiple specialized agents each do one job well
- Every answer is scored for quality before being returned
- Full monitoring: latency, token usage, and cost tracked per query
- Knowledge is stored and reused — future similar queries are faster

---

## ⚙️ How It Works

```
User Query (POST /ask)
        │
        ▼
  ┌─────────────┐
  │ Orchestrator │  ← Controls the entire flow
  └──────┬──────┘
         │
    ┌────▼────┐
    │Research │  → Searches the web
    │  Agent  │  → Stores results in ChromaDB
    └────┬────┘
         │
    ┌────▼────┐
    │Summarizer│  → Calls Gemini API
    │  Agent  │  → Produces structured summary
    └────┬────┘
         │
    ┌────▼────┐
    │Validator│  → Scores quality (0.0 – 1.0)
    │  Agent  │  → Writes final answer
    └────┬────┘
         │
    ┌────▼──────────────────────────┐
    │  Structured JSON Response     │
    │  answer + sources + score     │
    │  + latency + tokens + cost    │
    └───────────────────────────────┘
         │
    ┌────▼────┐
    │ Logger  │  → Saves everything to activity.log
    └─────────┘
```

---

## 🛠 Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| Backend Server | FastAPI + Uvicorn | REST API, async request handling |
| LLM | Google Gemini 1.5 Flash | Summarization, validation, answering |
| Vector Database | ChromaDB | Store and retrieve knowledge embeddings |
| Embeddings | sentence-transformers (MiniLM) | Convert text to vectors (free, local) |
| Web Search | SerpAPI (or built-in mock) | Fetch live web results |
| HTTP Client | HTTPX | Async-compatible web requests |
| Retry Logic | Tenacity | Auto-retry failed API calls |
| Environment | python-dotenv | Secure config management |
| Language | Python 3.10+ | Core language |

---

## ✅ Prerequisites

Before you begin, make sure you have the following:

| Requirement | Version | Check Command |
|---|---|---|
| Python | 3.10 or higher | `python --version` |
| pip | Latest | `pip --version` |
| Git | Any | `git --version` |
| Google Gemini API Key | Free tier works | [Get it here →](https://aistudio.google.com/app/apikey) |
| SerpAPI Key (optional) | Free: 100/mo | [Get it here →](https://serpapi.com) |

> **Note:** SerpAPI is optional. The system ships with a built-in mock search that works perfectly for testing and learning. Only set up SerpAPI when you need real-time web results.

---

## 📁 Project Structure

```
research-agent/
│
├── app/
│   ├── main.py                    # FastAPI server — all endpoints live here
│   ├── orchestrator.py            # Master controller — runs all agents in sequence
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── research_agent.py      # Searches web, stores results in ChromaDB
│   │   ├── summarizer_agent.py    # Condenses raw info using Gemini
│   │   └── validator_agent.py     # Scores quality, writes final answer
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   └── web_search.py          # Web search (mock or SerpAPI)
│   │
│   ├── vector_store/
│   │   ├── __init__.py
│   │   └── chroma_store.py        # ChromaDB wrapper (add, search, chunk)
│   │
│   ├── monitoring/
│   │   ├── __init__.py
│   │   └── logger.py              # JSON activity logger + stats calculator
│   │
│   └── utils/
│       ├── __init__.py
│       ├── gemini_client.py       # Gemini API wrapper with retry
│       ├── text_processor.py      # Cleaning, chunking, token + cost estimation
│       └── rag.py                 # RAG pipeline (retrieve → prompt → generate)
│
├── logs/
│   └── activity.log               # Auto-created on first query
│
├── chroma_db/                     # Auto-created by ChromaDB
│
├── .env                           # Your API keys (never commit this)
├── .env.example                   # Safe template to share
├── requirements.txt               # All Python dependencies
└── README.md                      # This file
```

---

## 🚀 Installation & Setup

### Step 1 — Clone the Repository

```bash
git clone https://github.com/your-username/research-agent.git
cd research-agent
```

### Step 2 — Create a Virtual Environment

```bash
# Create the virtual environment
python -m venv venv

# Activate it
# On macOS / Linux:
source venv/bin/activate

# On Windows (Command Prompt):
venv\Scripts\activate

# On Windows (PowerShell):
venv\Scripts\Activate.ps1
```

You should see `(venv)` in your terminal prompt.

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

This installs: FastAPI, ChromaDB, Google Generative AI SDK, sentence-transformers, HTTPX, and all other dependencies. First install may take 2–4 minutes (sentence-transformers model download).

### Step 4 — Create the Logs Directory

```bash
mkdir logs
```

---

## 🔑 Configuration

### Step 1 — Create your `.env` file

```bash
cp .env.example .env
```

Or create `.env` manually:

```env
# ── Required ────────────────────────────────────────────────
GEMINI_API_KEY=your_gemini_api_key_here

# ── Optional (leave blank to use mock search) ───────────────
SERPAPI_KEY=your_serpapi_key_here

# ── App Config ──────────────────────────────────────────────
ENVIRONMENT=development
LOG_FILE=logs/activity.log
```

### Step 2 — Get Your Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the key and paste it into your `.env` file

**Free Tier Limits (Gemini 1.5 Flash):**
- 15 requests per minute
- 1,000,000 tokens per day
- $0 cost within these limits
- Paid usage: ~$0.075 per 1M input tokens, ~$0.30 per 1M output tokens

### Step 3 — Test Your Gemini Key

```bash
python app/utils/gemini_client.py
```

Expected output:
```
Response: The capital of France is Paris.
Tokens used: 18
```

---

## ▶️ Running the Server

### Development Mode (with auto-reload)

```bash
python app/main.py
```

### Using Uvicorn Directly

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Verify the Server is Running

Open your browser and visit:

| URL | What You'll See |
|---|---|
| `http://localhost:8000/health` | `{"status": "ok", "version": "1.0.0"}` |
| `http://localhost:8000/docs` | Interactive Swagger UI for all endpoints |
| `http://localhost:8000/redoc` | Clean API documentation |

---

## 📡 API Endpoints

### `POST /ask` — Run the Research Agent

The main endpoint. Send a question, get a researched, validated answer.

**Request:**
```json
{
  "query": "What are the benefits of intermittent fasting?"
}
```

**Response:**
```json
{
  "answer": "Intermittent fasting has been shown to improve metabolic health by...",
  "sources": [
    "https://example.com/fasting-research",
    "https://healthstudy.org/if-benefits"
  ],
  "validation_score": 0.87,
  "recommendation": "PASS",
  "issues": [],
  "metrics": {
    "latency_seconds": 4.3,
    "total_tokens": 1920,
    "estimated_cost_usd": 0.000144,
    "breakdown": {
      "research_latency": 0.4,
      "summarizer_latency": 2.2,
      "validator_latency": 1.7,
      "chunks_stored": 6
    }
  }
}
```

---

### `GET /health` — Server Health Check

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "environment": "development",
  "version": "1.0.0"
}
```

---

### `GET /logs` — View Activity Logs

Returns recent query logs. Use for debugging and monitoring.

```bash
# Get last 10 logs
curl "http://localhost:8000/logs?limit=10"

# Get only failed queries
curl "http://localhost:8000/logs?event_type=query_failed"
```

```json
{
  "logs": [
    {
      "event": "query_completed",
      "query": "quantum computing advances",
      "validation_score": 0.84,
      "recommendation": "PASS",
      "metrics": { "latency_seconds": 4.1, "total_tokens": 1750 },
      "timestamp": "2024-07-15T10:23:41.123456"
    }
  ],
  "count": 1
}
```

---

### `GET /stats` — Aggregated System Statistics

```bash
curl http://localhost:8000/stats
```

```json
{
  "total_queries": 42,
  "successful": 40,
  "failed": 2,
  "avg_latency_seconds": 4.2,
  "avg_tokens_per_query": 1830,
  "total_cost_usd": 0.001232,
  "avg_cost_per_query": 0.000031
}
```

---

## 🧪 Testing the System

### Option 1 — Swagger UI (Easiest)

Go to `http://localhost:8000/docs`, click **POST /ask**, then **Try it out**, enter your query and hit **Execute**.

### Option 2 — cURL

```bash
# Basic query
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "How does transformer architecture work in AI?"}'
```

### Option 3 — Python Script

```python
import httpx

client = httpx.Client()

response = client.post(
    "http://localhost:8000/ask",
    json={"query": "What is retrieval augmented generation?"}
)

result = response.json()
print("Answer:", result["answer"])
print("Score:", result["validation_score"])
print("Cost:", result["metrics"]["estimated_cost_usd"])
```

### Option 4 — Test Individual Components

```bash
# Test Gemini API connection
python app/utils/gemini_client.py

# Test ChromaDB storage and search
python app/vector_store/chroma_store.py

# Test web search tool
python app/tools/web_search.py
```

---

## 💬 Example Queries & What You'll Get Back

### Technology & AI

| Query | What You Get |
|---|---|
| `"Explain how large language models work"` | Technical breakdown with key concepts, training process, limitations |
| `"What is the difference between RAG and fine-tuning?"` | Structured comparison with pros/cons, when to use each |
| `"Latest advances in quantum computing 2024"` | Summary of recent breakthroughs, key players, timelines |
| `"How does ChromaDB handle vector similarity search?"` | Explanation of HNSW algorithm, cosine similarity, use cases |

### Business & Finance

| Query | What You Get |
|---|---|
| `"What are the main risks of investing in AI stocks?"` | Risk categories, specific factors, historical context |
| `"How do startups raise Series A funding?"` | Step-by-step process, typical metrics, investor expectations |
| `"Explain supply chain disruption causes in 2024"` | Key factors, affected industries, mitigation strategies |

### Science & Health

| Query | What You Get |
|---|---|
| `"What are the health benefits of meditation?"` | Evidence-based findings, study references, practical insights |
| `"How does CRISPR gene editing work?"` | Mechanism explained simply, applications, ethical concerns |
| `"What causes inflation and how is it controlled?"` | Economic explanation, central bank tools, real examples |

### Each Response Always Includes:
- ✅ **Direct answer** — 2-4 clean sentences
- ✅ **Source URLs** — where the information came from
- ✅ **Validation score** — 0.0 to 1.0 quality rating
- ✅ **PASS / FAIL** — whether the answer meets quality threshold
- ✅ **Latency** — how long it took in seconds
- ✅ **Token count** — total tokens consumed
- ✅ **Cost** — estimated USD cost of the query

---

## 🏢 Real-World Use Cases

### 1. 📰 News & Research Aggregation Tool
**Who uses it:** Journalists, analysts, researchers  
**How:** Point the agent at topics like `"ESG investing trends Q3 2024"`. The system pulls current information, summarizes it, and scores reliability — saving hours of manual research.

### 2. 🎓 Corporate Knowledge Assistant
**Who uses it:** HR teams, new employees, internal support  
**How:** Pre-load company documents into ChromaDB. Employees ask questions like `"What is our parental leave policy?"` and get instant, sourced answers — no digging through wikis.

### 3. 🛒 E-Commerce Product Research Bot
**Who uses it:** Procurement teams, buyers  
**How:** Query competitor pricing, product specs, and market positioning. `"Compare top ERP software options for SMBs"` returns a structured comparison in seconds.

### 4. ⚖️ Legal & Compliance Research
**Who uses it:** Law firms, compliance officers  
**How:** Research regulatory changes quickly. `"What are GDPR data retention requirements for healthcare data?"` returns a structured, sourced answer with a quality score — faster than manual research, flagged for attorney review if score is low.

### 5. 💊 Medical Literature Summarizer
**Who uses it:** Doctors, medical students, researchers  
**How:** Query clinical topics: `"What does recent research say about metformin and longevity?"`. Gets synthesized summaries from research literature stored in ChromaDB.

### 6. 🤖 AI-Powered Customer Support Backend
**Who uses it:** SaaS companies  
**How:** Customer asks `"Why is my API returning a 429 error?"`. The agent searches the product knowledge base stored in ChromaDB and returns a validated, specific answer — reducing support ticket volume.

### 7. 📈 Investment Research Tool
**Who uses it:** Financial advisors, retail investors  
**How:** `"What are analysts saying about semiconductor stocks in 2024?"` returns a synthesized view of current sentiment with quality validation — disclosed as AI-generated, not financial advice.

### 8. 🎓 Personalized Learning Assistant
**Who uses it:** Students, self-learners  
**How:** `"Explain transformer attention mechanism like I'm a CS student"`. Gets a structured, validated explanation. Each answer stored in ChromaDB so follow-up questions are faster and context-aware.

---

## 📊 Monitoring & Logs

All activity is logged to `logs/activity.log` in JSON Lines format (one JSON object per line, easy to parse).

### Log Entry Example

```json
{
  "event": "query_completed",
  "query": "how does photosynthesis work",
  "validation_score": 0.91,
  "recommendation": "PASS",
  "metrics": {
    "latency_seconds": 3.8,
    "total_tokens": 1640,
    "estimated_cost_usd": 0.000123,
    "breakdown": {
      "research_latency": 0.3,
      "summarizer_latency": 2.0,
      "validator_latency": 1.5,
      "chunks_stored": 5
    }
  },
  "sources_count": 3,
  "intermediate": {
    "research_status": "success",
    "summary_snippet": "Photosynthesis is the process by which plants...",
    "validation_issues": []
  },
  "timestamp": "2024-07-15T14:32:09.456123"
}
```

### Reading Logs in Terminal

```bash
# View last 20 log entries (pretty printed)
tail -n 20 logs/activity.log | python -m json.tool

# Count total queries
wc -l logs/activity.log

# Find all failed queries
grep "query_failed" logs/activity.log

# Find queries that took longer than 6 seconds
grep "latency" logs/activity.log | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        d = json.loads(line)
        if d.get('metrics', {}).get('latency_seconds', 0) > 6:
            print(d['query'], '→', d['metrics']['latency_seconds'], 's')
    except: pass
"
```

---

## 💰 Cost Estimation

The system uses **Gemini 1.5 Flash** — the most cost-efficient model that handles this workload well.

| Pricing (Gemini 1.5 Flash) | Rate |
|---|---|
| Input tokens (≤128k context) | $0.075 per 1M tokens |
| Output tokens | $0.30 per 1M tokens |

### Typical Query Cost

| Component | Input Tokens | Output Tokens | Cost |
|---|---|---|---|
| Summarizer Agent | ~800 | ~400 | ~$0.000180 |
| Validator Agent | ~600 | ~300 | ~$0.000135 |
| **Total per query** | **~1,400** | **~700** | **~$0.000315** |

### Monthly Cost Estimates

| Usage Level | Queries/Month | Estimated Cost |
|---|---|---|
| Personal / Testing | 500 | ~$0.16 |
| Small Team | 5,000 | ~$1.60 |
| Production App | 50,000 | ~$16.00 |
| High Volume | 500,000 | ~$160.00 |

> Costs are estimates. Actual cost depends on query complexity and response length. The `/stats` endpoint shows your exact spend.

---

## 🔧 Troubleshooting

### `ModuleNotFoundError: No module named 'app'`
```bash
# Make sure you're running from the project root directory
cd research-agent
python app/main.py   # ✅ correct
```

### `Error: GEMINI_API_KEY not found`
```bash
# Check your .env file exists and has the key
cat .env
# Make sure there are no spaces around the = sign
# GEMINI_API_KEY=abc123   ✅
# GEMINI_API_KEY = abc123  ❌
```

### `ChromaDB: Collection already exists` error
```bash
# This is safe to ignore — the code uses get_or_create_collection
# If you want to reset the database:
rm -rf chroma_db/
```

### `429 Too Many Requests` from Gemini
```bash
# You've hit the free tier rate limit (15 RPM)
# The tenacity retry logic will handle this automatically
# If it keeps happening, wait 60 seconds and try again
```

### `sentence-transformers` download is slow
```
# First run downloads the MiniLM model (~90MB) — this is normal
# Subsequent runs are instant (model is cached in ~/.cache/huggingface/)
```

### Server starts but `/ask` returns 500
```bash
# Check the terminal for the full Python traceback
# Most likely cause: invalid Gemini API key or network issue
python app/utils/gemini_client.py   # test your key directly
```

---

## 🏭 Production Tips

### Enable Real Web Search
```env
# In your .env file, add your SerpAPI key:
SERPAPI_KEY=your_serpapi_key_here
```
Then in `app/tools/web_search.py`, change:
```python
# From:
results = search_web(query)
# To:
results = search_web(query, use_real_api=True)
```

### Run with Multiple Workers (for concurrent users)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Containerize with Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p logs
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t research-agent .
docker run -p 8000:8000 --env-file .env research-agent
```

### Cache Frequent Queries
Add a dictionary cache in `orchestrator.py` for queries that get asked repeatedly — saves API costs significantly in production.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/add-pdf-ingestion`
3. Commit your changes: `git commit -m "Add PDF document ingestion tool"`
4. Push and open a Pull Request

---

## 📄 License

MIT License — free to use, modify, and distribute. See `LICENSE` for details.

---

## 🙏 Acknowledgements

- [Google Gemini](https://ai.google.dev/) for the LLM backbone
- [ChromaDB](https://www.trychroma.com/) for the vector store
- [FastAPI](https://fastapi.tiangolo.com/) for the blazing-fast API framework
- [sentence-transformers](https://www.sbert.net/) for free, high-quality embeddings
- [SerpAPI](https://serpapi.com/) for web search integration

---

<div align="center">

**Built with ❤️ as a production-grade learning project**

[Report a Bug](https://github.com/your-username/research-agent/issues) · [Request a Feature](https://github.com/your-username/research-agent/issues)

</div>