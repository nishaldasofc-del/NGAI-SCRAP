# NGAI — Nishal Global Artificial Intelligence

> **Ultra Extreme Internet Intelligence Engine**

NGAI is a single-file, production-grade AI backend that combines distributed web scraping, LLM-powered data extraction, vector memory, multi-agent orchestration, trend detection, competitive intelligence, and a scheduled monitoring engine — all exposed through a clean FastAPI REST interface.

---

## Architecture

```
                        ┌─────────────────────────────┐
                        │        FastAPI  :8000        │
                        │   /ngai/*  (15+ routers)     │
                        └──────────────┬──────────────┘
                                       │
          ┌──────────────┬─────────────┼──────────────┬──────────────┐
          │              │             │              │              │
    ┌─────▼──────┐ ┌─────▼──────┐ ┌───▼──────┐ ┌────▼─────┐ ┌──────▼─────┐
    │  Scraper   │ │  AI Extract│ │  Vector  │ │  Celery  │ │ Multi-Agent│
    │  Engine    │ │  (LangChain│ │  Memory  │ │  Worker  │ │Orchestrator│
    │ Playwright │ │ /OpenRouter│ │  Qdrant  │ │  + Beat  │ │ 6 Agents   │
    └─────┬──────┘ └────────────┘ └──────────┘ └──────────┘ └────────────┘
          │
   ┌──────┼───────────────────────────────┐
   │      │                               │
┌──▼───┐ ┌▼─────┐ ┌────────┐ ┌─────────┐ │
│ PG   │ │Redis │ │ Qdrant │ │  MinIO  │ │
│:5432 │ │:6379 │ │ :6333  │ │  :9000  │ │
└──────┘ └──────┘ └────────┘ └─────────┘ │
└──────────────────────────────────────────┘
```

### Core components

| Component | Technology | Purpose |
|---|---|---|
| API | FastAPI + Uvicorn | REST endpoints, auth, rate limiting |
| Scraper | Playwright + httpx | JS-rendered & fast HTTP scraping |
| Extraction | LangChain + OpenRouter | HTML → structured JSON via LLM |
| Vector Memory | Qdrant | Semantic search over scraped intelligence |
| Embeddings | sentence-transformers / OpenAI | Text → vector conversion |
| Task Queue | Celery + Redis | Async/background scrape & crawl jobs |
| Scheduler | Celery Beat | Periodic monitor checks & prediction refresh |
| Object Storage | MinIO | Raw HTML and screenshot persistence |
| Database | PostgreSQL + SQLAlchemy | Jobs, extractions, alerts, datasets |

### Agents

| Agent | Endpoint | Purpose |
|---|---|---|
| Scraper | `POST /ngai/scrape` | Fetch URLs, extract, store to memory |
| Research | `POST /ngai/agents/run` | Deep research on a topic |
| Monitor | `POST /ngai/monitor` | Change detection on watched URLs |
| Trend | `POST /ngai/trend` | Trend & startup discovery |
| Competitor | `POST /ngai/competitor` | Competitive intelligence |
| Discovery | `POST /ngai/discovery` | Auto-discover & scrape sites on a topic |
| Dataset | `POST /ngai/dataset` | Build & export structured datasets |
| Orchestrator | `POST /ngai/orchestrator` | Master agent that delegates to all others |

---

## Quick start

### 1. Clone & configure

```bash
git clone <your-repo>
cd ngai
cp .env.example .env   # fill in your keys (see §Environment variables below)
```

### 2. Start all services with Docker Compose

```bash
docker compose up -d
```

Services started:

| Service | URL |
|---|---|
| NGAI API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/ngai/docs |
| ReDoc | http://localhost:8000/ngai/redoc |
| MinIO console | http://localhost:9001 |
| Qdrant dashboard | http://localhost:6333/dashboard |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

### 3. Verify

```bash
curl http://localhost:8000/ngai/health
```

---

## Local development (without Docker)

### Prerequisites

- Python 3.11+
- PostgreSQL 14+, Redis 7, Qdrant, MinIO running locally

### Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### Run the API

```bash
uvicorn ngai:app --host 0.0.0.0 --port 8000 --reload
```

### Run the Celery worker

```bash
celery -A ngai.celery_app worker --loglevel=info --concurrency=4
```

### Run Celery Beat (periodic tasks)

```bash
celery -A ngai.celery_app beat --loglevel=info
```

---

## Environment variables

Create a `.env` file in the project root. All variables are optional for local dev except `OPENROUTER_API_KEY`.

```dotenv
# ── Database ──────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://ngai:ngaisecret@localhost/ngai

# ── Redis ─────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── Qdrant ────────────────────────────────────────────────
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=ngai_knowledge

# ── MinIO ─────────────────────────────────────────────────
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=ngai_minio
MINIO_SECRET_KEY=ngai_minio_secret
MINIO_BUCKET=ngai-raw

# ── LLM via OpenRouter ────────────────────────────────────
# Get your key at https://openrouter.ai/keys
OPENROUTER_API_KEY=sk-or-...
# Any model slug from https://openrouter.ai/models
DEFAULT_LLM=google/gemini-flash-1.5

# ── Embeddings ────────────────────────────────────────────
# "local"  → sentence-transformers, no key needed (default)
# "openai" → OpenAI text-embedding-3-small, needs OPENAI_API_KEY
EMBEDDING_PROVIDER=local
OPENAI_API_KEY=

# ── Scraping ──────────────────────────────────────────────
MAX_CONCURRENT_SCRAPERS=10
REQUEST_TIMEOUT=30
USE_PLAYWRIGHT=true
MAX_CRAWL_DEPTH=3
# Comma-separated proxy URLs (optional)
# PROXY_LIST=http://proxy1:8080,http://proxy2:8080

# ── Security ──────────────────────────────────────────────
# Leave empty in dev — all requests will be accepted
# Comma-separated API keys in production
API_KEYS=
RATE_LIMIT_PER_MINUTE=60
ALLOWED_ORIGINS=http://localhost:3000

# ── Cache ─────────────────────────────────────────────────
CACHE_TTL_SECONDS=300
```

---

## API reference

All endpoints live under `/ngai/`. Pass your API key in the `X-NGAI-API-Key` header (not required when `API_KEYS` is empty).

### Search

```http
POST /ngai/search
Content-Type: application/json

{
  "query": "AI startups in climate tech",
  "top_k": 10,
  "live": false
}
```

### Scrape

```http
POST /ngai/scrape
Content-Type: application/json

{
  "urls": ["https://techcrunch.com", "https://example.com"],
  "schema": "article",
  "screenshot": false
}
```

Poll the job status:

```http
GET /ngai/scrape/{job_id}
```

### Analyze (single URL)

```http
POST /ngai/analyze
Content-Type: application/json

{
  "url": "https://example.com",
  "schema": "company"
}
```

### Predict

```http
POST /ngai/predict
Content-Type: application/json

{ "topic": "quantum computing" }
```

### Orchestrator (high-level goal)

```http
POST /ngai/orchestrator
Content-Type: application/json

{
  "goal": "Research the top 5 AI chip companies and their funding",
  "max_steps": 6
}
```

Full interactive documentation is available at **http://localhost:8000/ngai/docs**.

---

## Dockerfile

The `docker-compose.yml` expects a `Dockerfile` in the project root. A minimal example:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium --with-deps

COPY ngai.py .

EXPOSE 8000
```

---

## Periodic tasks (Celery Beat)

| Task | Schedule | Description |
|---|---|---|
| `ngai.task_run_monitors` | Every 5 minutes | Check all active `MonitorTarget` URLs for content changes |
| `ngai.task_refresh_predictions` | Every hour | Refresh trend predictions for default topics |

---

## Project structure

```
.
├── ngai.py               # Entire NGAI application (single-file architecture)
├── requirements.txt      # Python dependencies
├── docker-compose.yml    # Full infrastructure stack
├── Dockerfile            # Container image for API / worker / beat
└── .env                  # Environment configuration (not committed)
```

---

## License

This project is authored by **Nishal**. All rights reserved.
