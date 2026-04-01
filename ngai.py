"""
NGAI — Nishal Global Artificial Intelligence

Ultra Extreme Internet Intelligence Engine

Author: Nishal
System: NGAI Core
Architecture: Single File AI Infrastructure

Features:
- Multi Agent AI
- Distributed Scraper
- Prediction Engine
- Intelligence Search
- Vector Memory
- Monitoring Engine

NGAI = Nishal Global Artificial Intelligence

Sections (search with §):
  §CONFIG            Settings & environment
  §MODELS            SQLAlchemy ORM models
  §DATABASE          Async + sync DB sessions
  §VECTOR_MEMORY     Qdrant-backed semantic memory
  §SCRAPER_ENGINE    Playwright + httpx distributed scraper
  §AI_EXTRACTION     LLM HTML → structured JSON
  §MULTI_AGENT       Six specialised AI agents
  §TREND_AGENT       Trend detection & startup discovery
  §COMPETITOR_AGENT  Competitive intelligence & positioning
  §DISCOVERY_AGENT   Auto-discover, scrape & store websites
  §DATASET_AGENT     Build, export & training-data generation
  §ORCHESTRATOR_AGENT Master agent that controls all others
  §PREDICTION_ENGINE Trend detection & forecasting
  §MONITOR_ENGINE    Scheduled change detection
  §SEARCH_ENGINE     AI intelligence search
  §TASK_QUEUE        Celery distributed task queue
  §SECURITY          API-key auth + rate limiting
  §PERFORMANCE       Response caching layer
  §API_ROUTES        FastAPI routers (/ngai/*)
  §MAIN_APP          FastAPI app + lifespan
"""

from __future__ import annotations

# =============================================================================
# §CONFIG
# =============================================================================
import asyncio
import hashlib
import io
import json
import logging
import random
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from pydantic import BaseModel as PydanticModel, Field
from pydantic_settings import BaseSettings

log = logging.getLogger("ngai")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://ngai:ngaisecret@localhost/ngai"
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    # Vector DB
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "ngai_knowledge"
    # Object Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "ngai-raw"
    # LLMs — OpenRouter
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    # Pick any model slug from openrouter.ai/models
    # e.g. "google/gemini-flash-1.5", "meta-llama/llama-3.1-70b-instruct", "openai/gpt-4o"
    DEFAULT_LLM: str = "google/gemini-flash-1.5"
    # Embeddings: set EMBEDDING_PROVIDER=openai (needs OPENAI_API_KEY) or "local" (sentence-transformers, no key)
    EMBEDDING_PROVIDER: str = "local"
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 1536
    # Scraping
    MAX_CONCURRENT_SCRAPERS: int = 10
    REQUEST_TIMEOUT: int = 30
    PROXY_LIST: list[str] = []
    USE_PLAYWRIGHT: bool = True
    MAX_CRAWL_DEPTH: int = 3
    # Security
    API_KEYS: list[str] = []
    RATE_LIMIT_PER_MINUTE: int = 60
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]
    # Cache
    CACHE_TTL_SECONDS: int = 300

    model_config = {"env_file": ".env"}


settings = Settings()


# =============================================================================
# §MODELS
# =============================================================================
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, JSON, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class ScrapedPage(Base):
    __tablename__ = "scraped_pages"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url           = Column(String(2048), nullable=False, index=True)
    domain        = Column(String(255), index=True)
    raw_html_path = Column(String(512))
    status_code   = Column(String(10))
    content_hash  = Column(String(64), index=True)
    scraped_at    = Column(DateTime(timezone=True), default=utcnow)
    page_metadata = Column(JSON, default=dict)
    extractions   = relationship("Extraction", back_populates="page")


class Extraction(Base):
    __tablename__   = "extractions"
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id         = Column(UUID(as_uuid=True), ForeignKey("scraped_pages.id"))
    schema_name     = Column(String(100))
    structured_data = Column(JSON)
    summary         = Column(Text)
    entities        = Column(JSON, default=list)
    confidence      = Column(Float)
    extracted_at    = Column(DateTime(timezone=True), default=utcnow)
    page            = relationship("ScrapedPage", back_populates="extractions")


class ScrapeJob(Base):
    __tablename__  = "scrape_jobs"
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    urls           = Column(JSON)
    status         = Column(String(20), default="pending")
    task_id        = Column(String(100))
    created_at     = Column(DateTime(timezone=True), default=utcnow)
    completed_at   = Column(DateTime(timezone=True))
    config         = Column(JSON, default=dict)
    result_summary = Column(JSON, default=dict)


class MonitorTarget(Base):
    __tablename__    = "monitor_targets"
    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name             = Column(String(255))
    url              = Column(String(2048))
    interval_minutes = Column(Float, default=30)
    active           = Column(Boolean, default=True)
    alert_on_change  = Column(Boolean, default=True)
    last_checked     = Column(DateTime(timezone=True))
    last_hash        = Column(String(64))
    updated_at       = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AlertRecord(Base):
    __tablename__ = "alerts"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    monitor_id    = Column(UUID(as_uuid=True), ForeignKey("monitor_targets.id"), nullable=True)
    type          = Column(String(50))
    message       = Column(Text)
    payload       = Column(JSON)
    fired_at      = Column(DateTime(timezone=True), default=utcnow)
    read          = Column(Boolean, default=False)


class PredictionRecord(Base):
    __tablename__   = "predictions"
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic           = Column(String(512), index=True)
    prediction_json = Column(JSON)
    data_points     = Column(Integer, default=0)
    created_at      = Column(DateTime(timezone=True), default=utcnow)


class TrendRecord(Base):
    __tablename__  = "trend_records"
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query          = Column(String(512), index=True)
    trends         = Column(JSON, default=list)
    startups       = Column(JSON, default=list)
    market_signals = Column(JSON, default=list)
    confidence     = Column(Float, default=0.0)
    created_at     = Column(DateTime(timezone=True), default=utcnow)


class DatasetRecord(Base):
    __tablename__  = "datasets"
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name           = Column(String(255), index=True)
    description    = Column(Text)
    schema_name    = Column(String(100))
    rows           = Column(Integer, default=0)
    data           = Column(JSON, default=list)
    export_formats = Column(JSON, default=list)
    created_at     = Column(DateTime(timezone=True), default=utcnow)
    updated_at     = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class DiscoveryRecord(Base):
    __tablename__ = "discovery_records"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query         = Column(String(512), index=True)
    discovered    = Column(JSON, default=list)   # list of {url, domain, title, summary}
    scraped_count = Column(Integer, default=0)
    stored_count  = Column(Integer, default=0)
    created_at    = Column(DateTime(timezone=True), default=utcnow)


# =============================================================================
# §DATABASE
# =============================================================================
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session

async_engine = create_async_engine(
    settings.DATABASE_URL, echo=False,
    pool_size=10, max_overflow=20, pool_pre_ping=True,
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False,
)


async def init_db() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("NGAI database initialised")


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


_sync_url  = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
sync_engine = create_engine(_sync_url, pool_size=5, max_overflow=10, pool_pre_ping=True)
SyncSession = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)


@contextmanager
def get_sync_db() -> Session:
    session = SyncSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# =============================================================================
# §VECTOR_MEMORY
# =============================================================================
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    Distance, FieldCondition, Filter,
    MatchValue, PointStruct, ScoredPoint, VectorParams,
)


def _build_embed_fn():
    """
    Returns an async callable: text -> list[float].
    EMBEDDING_PROVIDER=openai  → OpenAI embeddings API (needs OPENAI_API_KEY)
    EMBEDDING_PROVIDER=local   → sentence-transformers running in-process (no key)
    anything else              → falls back to local
    """
    provider = settings.EMBEDDING_PROVIDER.lower()
    if provider == "openai" and settings.OPENAI_API_KEY:
        from openai import AsyncOpenAI as _OAI
        _client = _OAI(api_key=settings.OPENAI_API_KEY)
        async def _openai_embed(text: str) -> list[float]:
            r = await _client.embeddings.create(
                model=settings.EMBEDDING_MODEL, input=text[:8000],
            )
            return r.data[0].embedding
        log.info("Embedding provider: OpenAI (%s)", settings.EMBEDDING_MODEL)
        return _openai_embed
    else:
        # sentence-transformers — runs locally, no API key needed
        # pip install sentence-transformers
        try:
            from sentence_transformers import SentenceTransformer as _ST
            _model = _ST("all-MiniLM-L6-v2")   # 384-dim, fast, free
            # Override dim if using local model
            settings.__dict__["EMBEDDING_DIM"] = _model.get_sentence_embedding_dimension()
            log.info(
                "Embedding provider: local (all-MiniLM-L6-v2, dim=%d)",
                settings.EMBEDDING_DIM,
            )
            async def _local_embed(text: str) -> list[float]:
                loop = asyncio.get_event_loop()
                vec = await loop.run_in_executor(None, _model.encode, text[:8000])
                return vec.tolist()
            return _local_embed
        except ImportError:
            raise RuntimeError(
                "sentence-transformers is not installed and OPENAI_API_KEY is not set. "
                "Run: pip install sentence-transformers  "
                "Or set EMBEDDING_PROVIDER=openai and OPENAI_API_KEY in your .env"
            )


class VectorMemory:
    """Long-term semantic memory backed by Qdrant."""

    def __init__(self) -> None:
        self._client: Optional[AsyncQdrantClient] = None
        self._embed_fn = None   # initialised in connect()

    async def connect(self) -> None:
        self._client = AsyncQdrantClient(url=settings.QDRANT_URL)
        self._embed_fn = _build_embed_fn()
        await self._ensure_collection()
        log.info("NGAI vector memory connected -> %s", settings.QDRANT_URL)

    async def _ensure_collection(self) -> None:
        cols  = await self._client.get_collections()
        names = [c.name for c in cols.collections]
        if settings.QDRANT_COLLECTION not in names:
            await self._client.create_collection(
                collection_name=settings.QDRANT_COLLECTION,
                vectors_config=VectorParams(
                    size=settings.EMBEDDING_DIM, distance=Distance.COSINE,
                ),
            )
            log.info("Created Qdrant collection: %s", settings.QDRANT_COLLECTION)

    async def embed(self, text: str) -> list[float]:
        return await self._embed_fn(text)

    async def store(self, text: str, payload: dict) -> str:
        vector   = await self.embed(text)
        point_id = str(uuid.uuid4())
        await self._client.upsert(
            collection_name=settings.QDRANT_COLLECTION,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )
        return point_id

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filter_schema: Optional[str] = None,
        filter_domain: Optional[str] = None,
    ) -> list[ScoredPoint]:
        vector = await self.embed(query)
        conditions = []
        if filter_schema:
            conditions.append(FieldCondition(key="schema_name", match=MatchValue(value=filter_schema)))
        if filter_domain:
            conditions.append(FieldCondition(key="domain", match=MatchValue(value=filter_domain)))
        qfilter = Filter(must=conditions) if conditions else None
        return await self._client.search(
            collection_name=settings.QDRANT_COLLECTION,
            query_vector=vector,
            limit=top_k,
            query_filter=qfilter,
            with_payload=True,
        )

    async def recall(self, query: str, top_k: int = 5) -> list[dict]:
        hits = await self.search(query, top_k=top_k)
        return [{"score": h.score, **h.payload} for h in hits]

    async def forget(self, point_id: str) -> None:
        await self._client.delete(
            collection_name=settings.QDRANT_COLLECTION,
            points_selector=[point_id],
        )

    async def collection_size(self) -> int:
        info = await self._client.get_collection(settings.QDRANT_COLLECTION)
        return info.points_count


memory = VectorMemory()


async def init_vector_memory() -> None:
    await memory.connect()


# =============================================================================
# §SCRAPER_ENGINE
# =============================================================================
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

CAPTCHA_SIGNALS = [
    "g-recaptcha", "cf-challenge", "captcha", "robot",
    "are you human", "verify you are", "ddos-guard",
]


@dataclass
class ScrapeResult:
    url:        str
    html:       str
    status_code: int
    headers:    dict             = field(default_factory=dict)
    screenshot: Optional[bytes]  = None
    links:      list[str]        = field(default_factory=list)
    error:      Optional[str]    = None

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.html.encode()).hexdigest()

    @property
    def success(self) -> bool:
        return self.error is None and 200 <= self.status_code < 400

    @property
    def domain(self) -> str:
        return urlparse(self.url).netloc


class ProxyRotator:
    def __init__(self, proxies: list[str]) -> None:
        self._proxies = proxies
        self._idx = 0

    def next(self) -> Optional[str]:
        if not self._proxies:
            return None
        p = self._proxies[self._idx % len(self._proxies)]
        self._idx += 1
        return p


class RateLimiter:
    """Per-domain polite delay."""

    def __init__(self) -> None:
        self._last: dict[str, float] = {}

    async def wait(self, domain: str, min_delay: float = 1.0) -> None:
        now  = time.monotonic()
        gap  = min_delay - (now - self._last.get(domain, 0))
        if gap > 0:
            await asyncio.sleep(gap)
        self._last[domain] = time.monotonic()


_rate_limiter = RateLimiter()


class PlaywrightScraper:
    """
    Stealth Playwright scraper.
    Supports proxy rotation, CAPTCHA detection, auto-retry, screenshot capture.

    Usage:
        async with PlaywrightScraper() as scraper:
            result = await scraper.scrape("https://example.com")
    """

    def __init__(self, proxies: list[str] = None) -> None:
        self._proxies = ProxyRotator(proxies or settings.PROXY_LIST)
        self._browser: Optional[Browser] = None
        self._pw = None

    async def __aenter__(self):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox", "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        return self

    async def __aexit__(self, *_):
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    async def _make_context(self) -> BrowserContext:
        proxy = self._proxies.next()
        opts: dict = dict(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1280, "height": 800},
            java_script_enabled=True,
            locale="en-US",
            timezone_id="America/New_York",
        )
        if proxy:
            opts["proxy"] = {"server": proxy}
        ctx = await self._browser.new_context(**opts)
        await ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        )
        return ctx

    async def scrape(
        self,
        url: str,
        wait_for: str = "networkidle",
        screenshot: bool = False,
        extract_links: bool = True,
        max_retries: int = 3,
    ) -> ScrapeResult:
        domain = urlparse(url).netloc
        await _rate_limiter.wait(domain)

        for attempt in range(max_retries):
            ctx = None
            try:
                ctx  = await self._make_context()
                page: Page = await ctx.new_page()
                await page.route(
                    "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,mp4,webm}",
                    lambda r: r.abort(),
                )
                resp   = await page.goto(url, wait_until=wait_for,
                                         timeout=settings.REQUEST_TIMEOUT * 1000)
                status = resp.status if resp else 0
                html   = await page.content()

                if _is_captcha(html):
                    raise ValueError("CAPTCHA detected")

                links: list[str] = []
                if extract_links:
                    hrefs = await page.eval_on_selector_all(
                        "a[href]", "els => els.map(e => e.href)"
                    )
                    links = [h for h in hrefs if h.startswith("http")]

                shot = await page.screenshot(full_page=True) if screenshot else None
                return ScrapeResult(
                    url=url, html=html, status_code=status,
                    headers=dict(resp.headers) if resp else {},
                    screenshot=shot, links=links,
                )
            except Exception as exc:
                log.warning("Scrape attempt %d/%d failed for %s: %s",
                            attempt + 1, max_retries, url, exc)
                if attempt == max_retries - 1:
                    return ScrapeResult(url=url, html="", status_code=0, error=str(exc))
                await asyncio.sleep(2 ** attempt)
            finally:
                if ctx:
                    await ctx.close()

        return ScrapeResult(url=url, html="", status_code=0, error="max retries exceeded")


def _is_captcha(html: str) -> bool:
    lower = html.lower()
    return any(s in lower for s in CAPTCHA_SIGNALS)


async def fast_scrape(url: str) -> ScrapeResult:
    """Lightweight httpx fallback for non-JS pages."""
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    await _rate_limiter.wait(urlparse(url).netloc, min_delay=0.5)
    async with httpx.AsyncClient(
        timeout=settings.REQUEST_TIMEOUT, follow_redirects=True
    ) as client:
        try:
            r = await client.get(url, headers=headers)
            soup  = BeautifulSoup(r.text, "html.parser")
            links = [
                str(a["href"]) for a in soup.find_all("a", href=True)
                if str(a["href"]).startswith("http")
            ]
            return ScrapeResult(url=url, html=r.text, status_code=r.status_code, links=links)
        except Exception as exc:
            return ScrapeResult(url=url, html="", status_code=0, error=str(exc))


class BulkScraper:
    """Parallel scraper with semaphore-limited concurrency."""

    def __init__(self, concurrency: int = None, proxies: list[str] = None) -> None:
        self.concurrency = concurrency or settings.MAX_CONCURRENT_SCRAPERS
        self.proxies     = proxies or settings.PROXY_LIST

    async def scrape_all(self, urls: list[str], screenshot: bool = False) -> list[ScrapeResult]:
        sem = asyncio.Semaphore(self.concurrency)
        if settings.USE_PLAYWRIGHT:
            async with PlaywrightScraper(self.proxies) as scraper:
                async def _do(url: str) -> ScrapeResult:
                    async with sem:
                        await asyncio.sleep(random.uniform(0.3, 1.5))
                        return await scraper.scrape(url, screenshot=screenshot)
                return list(await asyncio.gather(*[_do(u) for u in urls]))
        else:
            async def _fast(url: str) -> ScrapeResult:
                async with sem:
                    return await fast_scrape(url)
            return list(await asyncio.gather(*[_fast(u) for u in urls]))


class DeepCrawler:
    """BFS domain crawler up to max_pages / max_depth."""

    def __init__(self, max_pages: int = 50, max_depth: int = None) -> None:
        self.max_pages = max_pages
        self.max_depth = max_depth or settings.MAX_CRAWL_DEPTH

    async def crawl(self, start_url: str) -> list[ScrapeResult]:
        domain  = urlparse(start_url).netloc
        visited: set[str] = set()
        queue:   list[tuple[str, int]] = [(start_url, 0)]
        results: list[ScrapeResult]    = []

        async with PlaywrightScraper() as scraper:
            while queue and len(results) < self.max_pages:
                url, depth = queue.pop(0)
                if url in visited or depth > self.max_depth:
                    continue
                visited.add(url)
                result = await scraper.scrape(url, extract_links=True)
                results.append(result)
                log.info("Crawled [%d/%d] depth=%d %s",
                         len(results), self.max_pages, depth, url)
                if depth < self.max_depth:
                    for link in result.links:
                        if urlparse(link).netloc == domain and link not in visited:
                            queue.append((link, depth + 1))
        return results


def html_to_text(html: str, max_chars: int = 8000) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    if len(text) > max_chars:
        log.debug("html_to_text: truncated %d -> %d chars", len(text), max_chars)
    return text[:max_chars]


def extract_sitemap_urls(sitemap_xml: str) -> list[str]:
    soup = BeautifulSoup(sitemap_xml, "xml")
    return [loc.get_text() for loc in soup.find_all("loc")]


# =============================================================================
# §AI_EXTRACTION
# =============================================================================
from langchain_openai import ChatOpenAI

def _make_llm(temperature: float = 0.0) -> ChatOpenAI:
    """
    Build a ChatOpenAI instance pointed at OpenRouter.
    All NGAI agents use this — swap DEFAULT_LLM in .env to change the model.
    Supported models: https://openrouter.ai/models
    """
    return ChatOpenAI(
        model=settings.DEFAULT_LLM,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        temperature=temperature,
        default_headers={
            "HTTP-Referer": "https://github.com/ngai",   # optional: shown in OpenRouter dashboard
            "X-Title": "NGAI — Nishal Global AI",
        },
    )
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser


class NGAIEntity(PydanticModel):
    type:       str   = Field(description="PERSON|ORG|LOCATION|PRODUCT|TECH|EVENT|MARKET")
    value:      str   = Field(description="The entity string")
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class ExtractionResult(PydanticModel):
    schema_name:     str               = Field(description="company|article|product|person|startup|market|other")
    structured_data: dict[str, Any]    = Field(description="All key facts as JSON")
    summary:         str               = Field(description="2-3 sentence summary")
    entities:        list[NGAIEntity]  = Field(default_factory=list)
    confidence:      float             = Field(ge=0.0, le=1.0)
    language:        str               = Field(default="en", description="ISO 639-1 language code")
    topics:          list[str]         = Field(default_factory=list)


_EXTRACTION_PROMPT = PromptTemplate(
    input_variables=["content", "schema_hint", "format_instructions"],
    template="""You are NGAI — an elite intelligence extraction AI.

Extract ALL structured information from the content below.
{schema_hint}

Content:
{content}

{format_instructions}

Rules:
- Return ONLY valid JSON — no markdown, no explanation
- Be exhaustive — extract every fact
- Detect content language (ISO 639-1 code)""",
)

_SCHEMA_HINTS: dict[str, str] = {
    "company":  "Extract: name, founder, founded_year, category, description, website, funding, valuation, employees, country, products.",
    "article":  "Extract: title, author, published_date, summary, topics, source, sentiment.",
    "product":  "Extract: name, brand, price, description, features, rating, availability, category.",
    "person":   "Extract: name, role, organization, bio, skills, social_links, achievements.",
    "startup":  "Extract: name, founder, category, stage, funding, description, investors, country.",
    "market":   "Extract: market_name, size, growth_rate, key_players, trends, forecast.",
}
_SCHEMA_HINT_AUTO = "Detect the best schema automatically and extract ALL relevant facts."


def _parse_json_safe(text: str) -> Optional[dict]:
    """Strip markdown fences then parse JSON — handles LLM output quirks."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


class AIExtractionEngine:
    """Singleton LLM extraction engine. All methods are async."""

    _llm:    Optional[ChatOpenAI]           = None
    _parser: Optional[PydanticOutputParser] = None

    @classmethod
    def get_llm(cls) -> ChatOpenAI:
        if cls._llm is None:
            cls._llm = _make_llm(temperature=0)
        return cls._llm

    @classmethod
    def get_parser(cls) -> PydanticOutputParser:
        if cls._parser is None:
            cls._parser = PydanticOutputParser(pydantic_object=ExtractionResult)
        return cls._parser

    async def extract(
        self,
        html: str,
        schema: Optional[str] = None,
        url: str = "",
    ) -> ExtractionResult:
        text   = html_to_text(html)
        hint   = _SCHEMA_HINTS.get(schema or "", _SCHEMA_HINT_AUTO)
        parser = self.get_parser()
        prompt = _EXTRACTION_PROMPT.format(
            content=text, schema_hint=hint,
            format_instructions=parser.get_format_instructions(),
        )
        response = await self.get_llm().ainvoke(prompt)
        return parser.parse(response.content)

    async def extract_batch(
        self, pages: list[dict]
    ) -> list[ExtractionResult | Exception]:
        tasks = [
            self.extract(p["html"], p.get("schema"), p.get("url", ""))
            for p in pages
        ]
        return list(await asyncio.gather(*tasks, return_exceptions=True))

    async def summarize(self, text: str, sentences: int = 3) -> str:
        r = await self.get_llm().ainvoke(
            f"Summarize in {sentences} specific sentences:\n\n{text[:4000]}"
        )
        return r.content.strip()


extractor = AIExtractionEngine()


# =============================================================================
# §MULTI_AGENT
# =============================================================================

@dataclass
class AgentTask:
    id:         str
    agent:      str
    input:      dict
    created_at: datetime      = field(default_factory=utcnow)
    result:     Optional[Any] = None
    error:      Optional[str] = None
    status:     str           = "pending"


class BaseAgent(ABC):
    name: str = "base"
    _llm: Optional[ChatOpenAI] = None

    @classmethod
    def get_llm(cls) -> ChatOpenAI:
        if cls._llm is None:
            cls._llm = _make_llm(temperature=0.2)
        return cls._llm

    async def run(self, task: AgentTask) -> AgentTask:
        task.status = "running"
        log.info("[%s] task %s started", self.name, task.id)
        try:
            task.result = await self.execute(task.input)
            task.status = "done"
        except Exception as exc:
            task.error  = str(exc)
            task.status = "failed"
            log.error("[%s] task %s failed: %s", self.name, task.id, exc)
        return task

    @abstractmethod
    async def execute(self, input_: dict) -> Any: ...

    async def think(self, prompt: str) -> str:
        r = await self.get_llm().ainvoke(prompt)
        return r.content.strip()


# ── NGAI Scraper Agent ────────────────────────────────────────────────────────
class NGAIScraperAgent(BaseAgent):
    """Fetches URLs, extracts intelligence, stores to vector memory."""
    name = "scraper"

    async def execute(self, input_: dict) -> dict:
        urls       = input_.get("urls") or ([input_["url"]] if input_.get("url") else [])
        urls       = [u for u in urls if u]
        schema     = input_.get("schema")
        screenshot = input_.get("screenshot", False)

        results = await BulkScraper().scrape_all(urls, screenshot=screenshot)
        stored, failed = [], []

        for r in results:
            if not r.success:
                failed.append({"url": r.url, "error": r.error})
                continue
            try:
                extraction = await extractor.extract(r.html, schema=schema, url=r.url)
                point_id   = await memory.store(
                    text=extraction.summary,
                    payload={
                        "url":             r.url,
                        "domain":          r.domain,
                        "schema_name":     extraction.schema_name,
                        "structured_data": extraction.structured_data,
                        "summary":         extraction.summary,
                        "entities":        [e.dict() for e in extraction.entities],
                        "topics":          extraction.topics,
                        "language":        extraction.language,
                        "confidence":      extraction.confidence,
                        "scraped_at":      utcnow().isoformat(),
                    },
                )
                stored.append({"url": r.url, "point_id": point_id, "schema": extraction.schema_name})
            except Exception as exc:
                failed.append({"url": r.url, "error": str(exc)})

        return {"scraped": len(results), "stored": stored, "failed": failed}


# ── NGAI Research Agent ────────────────────────────────────────────────────────
class NGAIResearchAgent(BaseAgent):
    """Deep research: memory recall + optional live scraping + LLM synthesis."""
    name = "research"

    async def execute(self, input_: dict) -> dict:
        query     = input_["query"]
        live_urls = input_.get("live_urls", [])
        top_k     = input_.get("top_k", 10)

        if live_urls:
            live_task = AgentTask(id=str(uuid.uuid4()), agent="scraper",
                                  input={"urls": live_urls})
            await NGAIScraperAgent().run(live_task)

        existing = await memory.recall(query, top_k=top_k)
        has_data = bool(existing)
        context  = (
            "\n\n".join(
                f"[{m.get('url','?')}]\n{m.get('summary','')}"
                for m in existing
            ) if has_data else "No scraped intelligence in memory."
        )
        note = "" if has_data else "\n[WARNING: No scraped data — answer from training knowledge only. Lower confidence.]"

        synthesis = await self.think(f"""You are NGAI Research Intelligence.

Query: {query}

Intelligence:
{context}

Provide:
1. Direct answer (specific facts)
2. Key findings (bullet list)
3. Notable entities (companies, people, technologies)
4. Confidence level (0-1)
5. Recommended sources to scrape next
{note}
Be concise and factual.""")

        return {
            "query":         query,
            "synthesis":     synthesis,
            "sources_used":  len(existing),
            "sources":       [m.get("url", "") for m in existing],
            "has_live_data": has_data,
        }


# ── NGAI Analyzer Agent ────────────────────────────────────────────────────────
class NGAIAnalyzerAgent(BaseAgent):
    """Analyses stored intelligence for patterns, opportunities, and risks."""
    name = "analyzer"

    async def execute(self, input_: dict) -> dict:
        topic  = input_["topic"]
        schema = input_.get("schema")
        top_k  = input_.get("top_k", 20)
        domain = input_.get("domain")

        hits = await memory.search(topic, top_k=top_k,
                                   filter_schema=schema, filter_domain=domain)
        if not hits:
            return {"topic": topic, "insights": "No data found in memory.", "count": 0}

        dump = "\n".join(
            f"[{i+1}] score={h.score:.2f} | {h.payload.get('summary','')} | url={h.payload.get('url','')}"
            for i, h in enumerate(hits)
        )
        raw = await self.think(f"""Analyse this NGAI intelligence dataset for '{topic}':

{dump}

Return JSON with keys:
patterns, key_entities, opportunities, risks, market_signals, summary, confidence""")

        insights = _parse_json_safe(raw) or {"raw": raw}
        return {"topic": topic, "count": len(hits), "insights": insights}


# ── NGAI Intelligence Agent ────────────────────────────────────────────────────
class NGAIIntelligenceAgent(BaseAgent):
    """Meta-agent: cross-references multiple topics into a comprehensive report."""
    name = "intelligence"

    async def execute(self, input_: dict) -> dict:
        topics   = input_.get("topics") or [input_.get("topic", "")]
        question = input_.get("question", f"Intelligence report on: {', '.join(topics)}")

        all_mems: list[dict] = []
        for t in topics:
            all_mems.extend(await memory.recall(t, top_k=8))

        seen: set[str] = set()
        unique = [m for m in all_mems if not (m.get("url","") in seen or seen.add(m.get("url","")))]

        context = "\n\n".join(
            f"[{m.get('url','?')} | score {m.get('score',0):.2f}]\n{m.get('summary','')}"
            for m in unique[:30]
        ) or "No data available."

        report = await self.think(f"""You are NGAI — Nishal Global Artificial Intelligence.

Question: {question}

Intelligence corpus ({len(unique)} sources):
{context}

Generate a comprehensive intelligence report:
1. Executive Summary
2. Key Findings (numbered)
3. Notable Players & Entities
4. Market / Sector Signals
5. Risks & Opportunities
6. Recommended Actions
7. Intelligence Confidence (0-1)

Be authoritative and specific.""")

        return {
            "question":      question,
            "topics":        topics,
            "report":        report,
            "sources_count": len(unique),
            "sources":       [m.get("url","") for m in unique],
        }


# ── NGAI Monitor Agent ─────────────────────────────────────────────────────────
class NGAIMonitorAgent(BaseAgent):
    """Checks a URL for content changes and stores diffs in memory."""
    name = "monitor"

    async def execute(self, input_: dict) -> dict:
        url  = input_["url"]
        prev = input_.get("previous_hash", "")

        async with PlaywrightScraper() as scraper:
            result = await scraper.scrape(url)

        if not result.success:
            return {"url": url, "changed": False, "error": result.error}

        new_hash = result.content_hash
        changed  = new_hash != prev
        summary  = ""

        if changed and prev:
            extraction = await extractor.extract(result.html, url=url)
            summary    = extraction.summary
            await memory.store(
                extraction.summary,
                {"url": url, "domain": result.domain, "schema_name": extraction.schema_name,
                 "summary": extraction.summary, "scraped_at": utcnow().isoformat(),
                 "change_detected": True},
            )

        return {"url": url, "changed": changed, "new_hash": new_hash, "summary": summary}


# =============================================================================
# §TREND_AGENT
# =============================================================================

class NGAITrendAgent(BaseAgent):
    """Detects trending startups, emerging markets, and growth signals from intelligence memory."""
    name = "trend"

    async def execute(self, input_: dict) -> dict:
        query  = input_.get("query", "technology trends")
        sector = input_.get("sector", "")
        top_k  = input_.get("top_k", 30)
        region = input_.get("region", "global")

        # Pull broad intelligence
        search_term = f"{sector} {query} startup market trend".strip()
        hits = await memory.search(search_term, top_k=top_k)

        if not hits:
            return {
                "query": query, "sector": sector, "region": region,
                "trends": [], "startups": [], "market_signals": [],
                "note": "No data in memory. Use /ngai/scrape to gather intelligence first.",
            }

        corpus = "\n".join(
            f"[{i+1}] score={h.score:.2f} | date={h.payload.get('scraped_at','?')[:10]} | "
            f"domain={h.payload.get('domain','')} | {h.payload.get('summary','')}"
            for i, h in enumerate(hits)
        )

        raw = await self.think(f"""You are NGAI Trend Intelligence Agent.

Query: "{query}" | Sector: "{sector}" | Region: "{region}"

Intelligence corpus ({len(hits)} sources):
{corpus}

Return ONLY valid JSON with this exact structure:
{{
  "emerging_trends": [
    {{"trend": "", "momentum": "high/medium/low", "evidence": "", "timeframe": ""}}
  ],
  "trending_startups": [
    {{"name": "", "sector": "", "stage": "", "growth_signal": "", "website": ""}}
  ],
  "market_growth_signals": [
    {{"market": "", "signal": "", "estimated_growth": "", "opportunity_score": 0.0}}
  ],
  "declining_areas": [],
  "hot_technologies": [],
  "investment_hotspots": [],
  "regional_insights": "",
  "overall_confidence": 0.0,
  "summary": ""
}}""")

        result = _parse_json_safe(raw) or {"raw": raw}

        # Persist to DB async-safe
        async with AsyncSessionLocal() as db:
            record = TrendRecord(
                query=query,
                trends=result.get("emerging_trends", []),
                startups=result.get("trending_startups", []),
                market_signals=result.get("market_growth_signals", []),
                confidence=result.get("overall_confidence", 0.0),
            )
            db.add(record)
            await db.commit()

        return {
            "query": query, "sector": sector, "region": region,
            "sources_analysed": len(hits),
            **result,
        }


# =============================================================================
# §COMPETITOR_AGENT
# =============================================================================

class NGAICompetitorAgent(BaseAgent):
    """Deep competitive intelligence: positioning, product comparison, market strategy."""
    name = "competitor"

    async def execute(self, input_: dict) -> dict:
        company    = input_.get("company", "")
        competitors = input_.get("competitors", [])   # optional explicit list
        market     = input_.get("market", "")
        top_k      = input_.get("top_k", 20)

        if not company:
            raise ValueError("'company' is required for competitor analysis")

        # Recall intelligence about the company AND the market
        company_mems  = await memory.recall(company, top_k=top_k)
        market_mems   = await memory.recall(f"{market} competitors {company}", top_k=top_k) if market else []
        all_mems      = {m.get("url",""): m for m in company_mems + market_mems}.values()

        corpus = "\n".join(
            f"[{m.get('domain','')}] {m.get('summary','')}" for m in all_mems
        ) or "No competitive data in memory."

        competitor_hint = (
            f"Known competitors to compare: {', '.join(competitors)}." if competitors else ""
        )

        raw = await self.think(f"""You are NGAI Competitive Intelligence Agent.

Company under analysis: "{company}"
Market: "{market}"
{competitor_hint}

Intelligence corpus:
{corpus}

Return ONLY valid JSON:
{{
  "company": "",
  "market_position": "",
  "strengths": [],
  "weaknesses": [],
  "competitors": [
    {{
      "name": "",
      "market_share_estimate": "",
      "key_differentiator": "",
      "threat_level": "high/medium/low",
      "product_comparison": {{
        "better_at": [],
        "worse_at": [],
        "unique_features": []
      }}
    }}
  ],
  "product_gaps": [],
  "pricing_intelligence": "",
  "recent_moves": [],
  "partnership_signals": [],
  "market_share_estimate": "",
  "strategic_recommendations": [],
  "competitive_score": 0.0,
  "confidence": 0.0
}}""")

        return {
            "company": company,
            "market": market,
            "sources_analysed": len(list(all_mems)),
            **(
                _parse_json_safe(raw) or {"raw": raw}
            ),
        }


# =============================================================================
# §DISCOVERY_AGENT
# =============================================================================

class NGAIDiscoveryAgent(BaseAgent):
    """Auto-discovers relevant websites for a query, scrapes them, and stores to memory."""
    name = "discovery"

    # Seed URL templates for auto-discovery
    _SEED_TEMPLATES: list[str] = [
        "https://techcrunch.com/search/{kw}",
        "https://news.ycombinator.com/search?q={kw}",
        "https://www.producthunt.com/search?q={kw}",
        "https://crunchbase.com/search/organizations?q={kw}",
        "https://www.reddit.com/search/?q={kw}&type=link",
        "https://medium.com/search?q={kw}",
        "https://venturebeat.com/?s={kw}",
        "https://www.startupranking.com/search?q={kw}",
    ]

    async def execute(self, input_: dict) -> dict:
        query      = input_.get("query", "")
        max_sites  = min(int(input_.get("max_sites", 5)), 15)
        schema     = input_.get("schema")
        deep_crawl = input_.get("deep_crawl", False)

        if not query:
            raise ValueError("'query' is required for discovery")

        kw = query.lower().replace(" ", "+")
        seed_urls = [t.format(kw=kw) for t in self._SEED_TEMPLATES[:max_sites]]

        log.info("[discovery] Probing %d seed URLs for: %s", len(seed_urls), query)

        # Phase 1 – scrape seed pages
        seed_results = await BulkScraper().scrape_all(seed_urls)
        discovered: list[dict] = []

        for r in seed_results:
            if not r.success:
                continue
            # Extract outbound links as further discovery targets
            soup = BeautifulSoup(r.html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("http") and urlparse(href).netloc not in (
                    "techcrunch.com", "ycombinator.com", "reddit.com",
                    "medium.com", "venturebeat.com",
                ):
                    discovered.append({"url": href, "source": r.url})
                    if len(discovered) >= max_sites * 3:
                        break

        # Phase 2 – deduplicate and scrape discovered targets
        seen: set[str] = set()
        target_urls: list[str] = []
        for d in discovered:
            u = d["url"]
            dom = urlparse(u).netloc
            if dom not in seen:
                seen.add(dom)
                target_urls.append(u)
            if len(target_urls) >= max_sites:
                break

        if deep_crawl:
            target_urls = seed_urls[:max_sites] + target_urls[:max_sites]

        log.info("[discovery] Scraping %d discovered targets", len(target_urls))
        target_results = await BulkScraper().scrape_all(target_urls)

        stored, failed = [], []
        for r in target_results:
            if not r.success:
                failed.append({"url": r.url, "error": r.error})
                continue
            try:
                extraction = await extractor.extract(r.html, schema=schema, url=r.url)
                point_id   = await memory.store(
                    text=extraction.summary,
                    payload={
                        "url":             r.url,
                        "domain":          r.domain,
                        "schema_name":     extraction.schema_name,
                        "structured_data": extraction.structured_data,
                        "summary":         extraction.summary,
                        "entities":        [e.dict() for e in extraction.entities],
                        "topics":          extraction.topics,
                        "language":        extraction.language,
                        "confidence":      extraction.confidence,
                        "scraped_at":      utcnow().isoformat(),
                        "discovered_by":   "NGAIDiscoveryAgent",
                        "query":           query,
                    },
                )
                stored.append({"url": r.url, "domain": r.domain, "point_id": point_id})
            except Exception as exc:
                failed.append({"url": r.url, "error": str(exc)})

        # Persist discovery record
        async with AsyncSessionLocal() as db:
            rec = DiscoveryRecord(
                query=query,
                discovered=[{"url": s["url"], "domain": urlparse(s["url"]).netloc} for s in stored],
                scraped_count=len(target_results),
                stored_count=len(stored),
            )
            db.add(rec)
            await db.commit()

        return {
            "query":          query,
            "seeds_probed":   len(seed_urls),
            "sites_found":    len(target_urls),
            "stored":         stored,
            "failed":         failed,
            "stored_count":   len(stored),
            "failed_count":   len(failed),
        }


# =============================================================================
# §DATASET_AGENT
# =============================================================================

class NGAIDatasetAgent(BaseAgent):
    """Builds structured datasets from memory, supports export and training-data generation."""
    name = "dataset"

    async def execute(self, input_: dict) -> dict:
        action     = input_.get("action", "build")   # build | export | list | delete
        name       = input_.get("name", f"dataset_{utcnow().strftime('%Y%m%d_%H%M%S')}")
        query      = input_.get("query", "")
        schema     = input_.get("schema")
        top_k      = min(int(input_.get("top_k", 50)), 200)
        fmt        = input_.get("format", "json")     # json | jsonl | csv | training
        dataset_id = input_.get("dataset_id")

        if action == "list":
            async with AsyncSessionLocal() as db:
                from sqlalchemy import select
                rows = (await db.execute(select(DatasetRecord).order_by(DatasetRecord.created_at.desc()).limit(50))).scalars().all()
            return {"datasets": [
                {"id": str(r.id), "name": r.name, "rows": r.rows,
                 "schema": r.schema_name, "created_at": r.created_at.isoformat()}
                for r in rows
            ]}

        if action == "export" and dataset_id:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import select
                row = (await db.execute(select(DatasetRecord).where(DatasetRecord.id == uuid.UUID(dataset_id)))).scalar_one_or_none()
            if not row:
                return {"error": f"Dataset {dataset_id} not found"}
            return self._format_export(row.data, fmt, row.name)

        # action == "build"
        if not query:
            raise ValueError("'query' is required to build a dataset")

        hits = await memory.search(query, top_k=top_k, filter_schema=schema)
        if not hits:
            return {"name": name, "rows": 0, "note": "No matching data in memory"}

        # Build rows
        rows_data = []
        for h in hits:
            p = h.payload
            row_item = {
                "url":          p.get("url", ""),
                "domain":       p.get("domain", ""),
                "schema":       p.get("schema_name", ""),
                "summary":      p.get("summary", ""),
                "entities":     p.get("entities", []),
                "topics":       p.get("topics", []),
                "confidence":   p.get("confidence", 0.0),
                "language":     p.get("language", ""),
                "scraped_at":   p.get("scraped_at", ""),
                "structured":   p.get("structured_data", {}),
                "score":        round(h.score, 4),
            }
            rows_data.append(row_item)

        # Optionally enrich as training data
        if fmt == "training":
            rows_data = await self._build_training_pairs(rows_data, query)

        # Persist dataset
        async with AsyncSessionLocal() as db:
            record = DatasetRecord(
                name=name,
                description=f"Dataset built for query: {query}",
                schema_name=schema or "mixed",
                rows=len(rows_data),
                data=rows_data,
                export_formats=["json", "jsonl", "csv", "training"],
            )
            db.add(record)
            await db.commit()
            dataset_id_str = str(record.id)

        export = self._format_export(rows_data, fmt, name)
        return {
            "name":       name,
            "dataset_id": dataset_id_str,
            "query":      query,
            "rows":       len(rows_data),
            "format":     fmt,
            **export,
        }

    def _format_export(self, data: list, fmt: str, name: str) -> dict:
        if fmt == "jsonl":
            content = "\n".join(json.dumps(r, default=str) for r in data)
            return {"format": "jsonl", "content": content, "rows": len(data)}
        if fmt == "csv":
            if not data:
                return {"format": "csv", "content": "", "rows": 0}
            import io, csv as csvlib
            buf = io.StringIO()
            writer = csvlib.DictWriter(buf, fieldnames=list(data[0].keys()))
            writer.writeheader()
            for r in data:
                flat = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in r.items()}
                writer.writerow(flat)
            return {"format": "csv", "content": buf.getvalue(), "rows": len(data)}
        if fmt == "training":
            return {"format": "training", "data": data, "rows": len(data)}
        # default json
        return {"format": "json", "data": data, "rows": len(data)}

    async def _build_training_pairs(self, rows: list[dict], query: str) -> list[dict]:
        """Convert rows into instruction-response training pairs."""
        pairs = []
        for r in rows:
            if not r.get("summary"):
                continue
            pairs.append({
                "instruction": f"What do you know about {r.get('domain','this site')} related to: {query}?",
                "input":       r.get("url", ""),
                "output":      r.get("summary", ""),
                "metadata":    {
                    "schema":     r.get("schema"),
                    "confidence": r.get("confidence"),
                    "entities":   r.get("entities"),
                },
            })
        return pairs


# =============================================================================
# §ORCHESTRATOR_AGENT
# =============================================================================

class OrchestratorPlan(PydanticModel):
    """LLM-generated execution plan for the orchestrator."""
    agents:   list[str] = Field(default_factory=list)
    strategy: str       = ""
    steps:    list[dict] = Field(default_factory=list)


class NGAIOrchestratorAgent(BaseAgent):
    """
    Master orchestrator — plans and executes multi-agent pipelines.
    Given any high-level goal it generates a step-by-step agent execution plan,
    runs each agent in sequence (passing outputs forward), and synthesises a
    final intelligence report.

    Example: "Find AI startups in India"
      → plan: [discovery → scraper → research → analyzer → trend → intelligence]
      → each agent's output feeds the next
      → final synthesis returned
    """
    name = "orchestrator"

    # Map from plan keyword → agent name
    _AGENT_MAP = {
        "discovery":    "discovery",
        "discover":     "discovery",
        "scrape":       "scraper",
        "scraper":      "scraper",
        "research":     "research",
        "analyze":      "analyzer",
        "analyse":      "analyzer",
        "analyzer":     "analyzer",
        "trend":        "trend",
        "trends":       "trend",
        "competitor":   "competitor",
        "compete":      "competitor",
        "dataset":      "dataset",
        "intelligence": "intelligence",
        "predict":      "predict",
        "monitor":      "monitor",
    }

    async def execute(self, input_: dict) -> dict:
        goal      = input_.get("goal", input_.get("query", ""))
        context   = input_.get("context", {})
        max_steps = int(input_.get("max_steps", 6))

        if not goal:
            raise ValueError("'goal' or 'query' is required for the orchestrator")

        log.info("[orchestrator] Goal: %s", goal)

        # ── Step 1: Planning ──────────────────────────────────────────────────
        plan_raw = await self.think(f"""You are NGAI Orchestrator — the master intelligence controller.

User Goal: "{goal}"
Available Agents: discovery, scraper, research, analyzer, trend, competitor, dataset, intelligence, monitor

Design an execution plan. Think about what agents to run, in what order, with what inputs.
Each step should pass useful context to the next.

Return ONLY valid JSON:
{{
  "strategy": "brief explanation of the plan",
  "steps": [
    {{
      "step": 1,
      "agent": "agent_name",
      "reason": "why this agent at this step",
      "input_template": {{}}
    }}
  ]
}}

Rules:
- Maximum {max_steps} steps
- First step is usually "discovery" (find sites) or "scraper" (if URLs given)
- Always end with "intelligence" or "research" for final synthesis
- Use "trend" if goal involves market/startup discovery
- Use "competitor" if goal involves competitive analysis
- Use "dataset" only if user explicitly wants data export
""")

        plan = _parse_json_safe(plan_raw) or {}
        steps: list[dict] = plan.get("steps", [])
        strategy: str     = plan.get("strategy", "Sequential intelligence pipeline")

        if not steps:
            # Fallback default pipeline
            steps = [
                {"step": 1, "agent": "discovery",    "reason": "Find relevant websites", "input_template": {"query": goal}},
                {"step": 2, "agent": "research",     "reason": "Research gathered intelligence", "input_template": {"query": goal}},
                {"step": 3, "agent": "analyzer",     "reason": "Analyse patterns and insights", "input_template": {"topic": goal}},
                {"step": 4, "agent": "intelligence", "reason": "Synthesise final report", "input_template": {"question": goal, "topics": goal.split()[:5]}},
            ]

        log.info("[orchestrator] Plan: %s steps | strategy: %s", len(steps), strategy)

        # ── Step 2: Execution ─────────────────────────────────────────────────
        execution_log: list[dict] = []
        pipeline_context: dict    = {"goal": goal, "original_input": input_, **context}
        last_result: dict         = {}

        for step in steps[:max_steps]:
            agent_name = step.get("agent", "")
            if agent_name not in _AGENT_REGISTRY:
                log.warning("[orchestrator] Unknown agent in plan: %s — skipping", agent_name)
                continue

            # Build agent input by merging template with accumulated pipeline context
            template   = step.get("input_template", {})
            agent_input = self._build_agent_input(agent_name, template, pipeline_context, last_result, goal)

            log.info("[orchestrator] Step %s → %s | input keys: %s",
                     step.get("step"), agent_name, list(agent_input.keys()))

            task   = AgentTask(id=str(uuid.uuid4()), agent=agent_name, input=agent_input)
            result = await get_agent(agent_name).run(task)

            step_record = {
                "step":       step.get("step"),
                "agent":      agent_name,
                "reason":     step.get("reason", ""),
                "status":     result.status,
                "error":      result.error,
                "output_keys": list(result.result.keys()) if isinstance(result.result, dict) else [],
            }
            execution_log.append(step_record)

            if result.status == "done" and result.result:
                last_result = result.result if isinstance(result.result, dict) else {"result": result.result}
                pipeline_context.update({f"step_{step.get('step')}_result": last_result})

        # ── Step 3: Final synthesis ───────────────────────────────────────────
        context_dump = json.dumps(pipeline_context, default=str, indent=2)[:8000]
        synthesis = await self.think(f"""You are NGAI Master Intelligence Synthesiser.

Original Goal: "{goal}"
Pipeline Strategy: {strategy}
Execution Steps: {len(execution_log)}

Pipeline Context Summary:
{context_dump}

Generate a comprehensive final intelligence report:
1. Mission Summary (what was accomplished)
2. Key Discoveries
3. Top Findings (numbered, specific)
4. Notable Entities (companies, people, markets)
5. Actionable Recommendations
6. Data Quality & Confidence
7. Suggested Follow-up Actions

Be authoritative, specific, and data-driven.""")

        return {
            "goal":          goal,
            "strategy":      strategy,
            "steps_planned": len(steps),
            "steps_executed": len(execution_log),
            "execution_log": execution_log,
            "synthesis":     synthesis,
            "pipeline_context_keys": list(pipeline_context.keys()),
        }

    def _build_agent_input(
        self,
        agent_name: str,
        template: dict,
        ctx: dict,
        last_result: dict,
        goal: str,
    ) -> dict:
        """Build smart agent input by merging template with pipeline context."""
        inp = dict(template)
        g   = goal

        # Inject goal-derived defaults per agent type
        defaults: dict[str, dict] = {
            "discovery":    {"query": g, "max_sites": 5},
            "scraper":      {"urls": last_result.get("stored", [{}])[:3] or [], "schema": None},
            "research":     {"query": g, "top_k": 10},
            "analyzer":     {"topic": g, "top_k": 20},
            "trend":        {"query": g, "sector": "", "region": "global"},
            "competitor":   {"company": g, "market": ""},
            "dataset":      {"query": g, "action": "build", "top_k": 50},
            "intelligence": {"question": g, "topics": g.split()[:5]},
            "monitor":      {"url": last_result.get("url", ""), "previous_hash": ""},
        }

        base = defaults.get(agent_name, {})
        merged = {**base, **inp}

        # If discovery just ran, feed its stored URLs to the next scraper
        if agent_name == "scraper" and not merged.get("urls"):
            stored = last_result.get("stored", [])
            merged["urls"] = [s["url"] for s in stored if isinstance(s, dict) and "url" in s][:10]

        # Remove empty lists/strings that would cause agent failures
        return {k: v for k, v in merged.items() if v != "" or k in ("schema", "region")}


# ── Agent Registry ─────────────────────────────────────────────────────────────
_AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "scraper":      NGAIScraperAgent,
    "research":     NGAIResearchAgent,
    "analyzer":     NGAIAnalyzerAgent,
    "intelligence": NGAIIntelligenceAgent,
    "monitor":      NGAIMonitorAgent,
    "trend":        NGAITrendAgent,
    "competitor":   NGAICompetitorAgent,
    "discovery":    NGAIDiscoveryAgent,
    "dataset":      NGAIDatasetAgent,
    "orchestrator": NGAIOrchestratorAgent,
}


def get_agent(name: str) -> BaseAgent:
    cls = _AGENT_REGISTRY.get(name)
    if not cls:
        raise ValueError(f"Unknown agent '{name}'. Available: {list(_AGENT_REGISTRY)}")
    return cls()


# =============================================================================
# §PREDICTION_ENGINE
# =============================================================================

class PredictionEngine:
    """Trend detection, market forecasting, startup detection, competitor tracking."""

    _llm: Optional[ChatOpenAI] = None

    @classmethod
    def get_llm(cls) -> ChatOpenAI:
        if cls._llm is None:
            cls._llm = _make_llm(temperature=0.3)
        return cls._llm

    async def predict(self, topic: str, top_k: int = 30) -> dict:
        mems  = await memory.recall(topic, top_k=top_k)
        texts = "\n".join(
            f"- [{m.get('scraped_at','?')[:10]}] {m.get('summary','')}"
            for m in mems
        ) or "No data available."

        raw = await self.get_llm().ainvoke(f"""You are NGAI Prediction Engine.

Intelligence stream about '{topic}':
{texts}

Return JSON:
{{
  "emerging_trends": [],
  "declining_signals": [],
  "30_day_forecast": "",
  "confidence": 0.0,
  "key_drivers": [],
  "market_opportunities": [],
  "risk_factors": [],
  "recommended_tracking": []
}}""")

        prediction = _parse_json_safe(raw.content) or {"raw_prediction": raw.content}
        return {
            "topic":        topic,
            "data_points":  len(mems),
            "prediction":   prediction,
            "generated_at": utcnow().isoformat(),
        }

    async def detect_startups(self, sector: str) -> dict:
        hits = await memory.search(f"startup {sector}", top_k=20, filter_schema="startup")
        if not hits:
            return {"sector": sector, "startups": [], "note": "No startup data in memory"}
        context = "\n".join(h.payload.get("summary","") for h in hits)
        raw = await self.get_llm().ainvoke(
            f"From this intelligence about '{sector}' startups:\n{context}\n\n"
            "Return a JSON array: [{\"name\":\"\",\"stage\":\"\",\"funding\":\"\",\"why_interesting\":\"\"}]"
        )
        startups = _parse_json_safe(raw.content) or []
        return {"sector": sector, "startups": startups, "sources": len(hits)}

    async def competitor_track(self, company: str) -> dict:
        mems    = await memory.recall(company, top_k=15)
        context = "\n".join(m.get("summary","") for m in mems) or "No data."
        raw = await self.get_llm().ainvoke(
            f"Track competitive intelligence for '{company}':\n{context}\n\n"
            "Return JSON: {\"company\":\"\",\"recent_moves\":[],\"product_launches\":[],"
            "\"partnerships\":[],\"threats\":[],\"opportunities\":[],\"competitive_score\":0.0}"
        )
        return _parse_json_safe(raw.content) or {"company": company, "raw": raw.content}


prediction_engine = PredictionEngine()


# =============================================================================
# §MONITOR_ENGINE
# =============================================================================

def _run_sync(coro) -> Any:
    """Run async coroutine from sync context (Celery workers)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class MonitorEngine:
    """Manages scheduled URL monitoring. run_all_sync() called by Celery Beat."""

    async def check_target(self, target: MonitorTarget) -> dict:
        task = AgentTask(
            id=str(uuid.uuid4()), agent="monitor",
            input={"url": target.url, "previous_hash": target.last_hash or ""},
        )
        result = await NGAIMonitorAgent().run(task)
        return result.result or {}

    def run_all_sync(self) -> None:
        with get_sync_db() as session:
            targets = (
                session.query(MonitorTarget)
                .filter(MonitorTarget.active == True)
                .all()
            )
            log.info("MonitorEngine: checking %d targets", len(targets))
            for target in targets:
                result = _run_sync(self.check_target(target))
                if result.get("changed"):
                    session.add(AlertRecord(
                        monitor_id=target.id,
                        type="change",
                        message=f"Content changed at {target.url}",
                        payload=result,
                    ))
                    target.last_hash    = result["new_hash"]
                    target.last_checked = utcnow()
                    log.info("Change detected: %s", target.url)
            session.commit()


monitor_engine = MonitorEngine()


# =============================================================================
# §SEARCH_ENGINE
# =============================================================================

class NGAISearchEngine:
    """
    NGAI AI Intelligence Search.
    Flow: query -> memory recall -> [optional live scrape] -> LLM synthesis -> ranked results.
    """

    async def search(
        self,
        query: str,
        top_k: int = 10,
        live: bool = False,
        schema: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> dict:
        if live:
            await self._live_scrape(query)

        hits = await memory.search(query, top_k=top_k,
                                   filter_schema=schema, filter_domain=domain)
        if not hits:
            return {
                "query":     query,
                "results":   [],
                "synthesis": "No intelligence found. Use /ngai/scrape to gather data first.",
                "total":     0,
            }

        results = [
            {
                "rank":       i + 1,
                "score":      round(h.score, 4),
                "url":        h.payload.get("url", ""),
                "domain":     h.payload.get("domain", ""),
                "summary":    h.payload.get("summary", ""),
                "schema":     h.payload.get("schema_name", ""),
                "entities":   h.payload.get("entities", []),
                "topics":     h.payload.get("topics", []),
                "scraped_at": h.payload.get("scraped_at", ""),
            }
            for i, h in enumerate(hits)
        ]

        context   = "\n".join(f"[{r['rank']}] ({r['domain']}) {r['summary']}" for r in results)
        synthesis = await AIExtractionEngine.get_llm(AIExtractionEngine).ainvoke(
            f"You are NGAI Search Intelligence. Answer using these results:\n\n"
            f"Query: {query}\n\nResults:\n{context}\n\n"
            f"Give a direct, fact-rich answer in 3-5 sentences. Cite sources by number."
        )

        return {
            "query":     query,
            "results":   results,
            "synthesis": synthesis.content.strip(),
            "total":     len(results),
        }

    async def _live_scrape(self, query: str) -> None:
        kw  = query.lower().replace(" ", "+")
        urls = [
            f"https://techcrunch.com/search/{kw}",
            f"https://news.ycombinator.com/search?q={kw}",
        ]
        for r in await BulkScraper().scrape_all(urls):
            if r.success:
                try:
                    ex = await extractor.extract(r.html, url=r.url)
                    await memory.store(ex.summary, {
                        "url": r.url, "domain": r.domain,
                        "schema_name": ex.schema_name, "summary": ex.summary,
                        "scraped_at": utcnow().isoformat(),
                    })
                except Exception as exc:
                    log.warning("Live scrape failed for %s: %s", r.url, exc)


search_engine = NGAISearchEngine()


# =============================================================================
# §TASK_QUEUE
# =============================================================================
from celery import Celery, shared_task
from celery.schedules import crontab

celery_app = Celery(
    "ngai",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["ngai"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    beat_schedule={
        "ngai-monitors-every-5min": {
            "task": "ngai.task_run_monitors",
            "schedule": crontab(minute="*/5"),
        },
        "ngai-predictions-hourly": {
            "task": "ngai.task_refresh_predictions",
            "schedule": crontab(minute=0),
        },
    },
)


@shared_task(bind=True, name="ngai.task_scrape_urls", max_retries=3, default_retry_delay=30)
def task_scrape_urls(self, urls: list, schema: str = None, screenshot: bool = False):
    task = AgentTask(
        id=str(uuid.uuid4()), agent="scraper",
        input={"urls": urls, "schema": schema, "screenshot": screenshot},
    )
    result = _run_sync(NGAIScraperAgent().run(task))
    if result.status == "failed":
        raise self.retry(exc=Exception(result.error))
    return result.result


@shared_task(bind=True, name="ngai.task_research", max_retries=2, default_retry_delay=60)
def task_research(self, query: str, live_urls: list = None):
    task = AgentTask(
        id=str(uuid.uuid4()), agent="research",
        input={"query": query, "live_urls": live_urls or []},
    )
    result = _run_sync(NGAIResearchAgent().run(task))
    return result.result


@shared_task(name="ngai.task_run_monitors")
def task_run_monitors():
    monitor_engine.run_all_sync()


@shared_task(name="ngai.task_refresh_predictions")
def task_refresh_predictions():
    for topic in ["AI", "machine learning", "startups", "crypto", "climate tech"]:
        try:
            r = _run_sync(prediction_engine.predict(topic))
            log.info("Prediction refreshed: '%s' (%d points)", topic, r["data_points"])
        except Exception as exc:
            log.error("Prediction refresh failed for '%s': %s", topic, exc)


@shared_task(name="ngai.task_deep_crawl")
def task_deep_crawl(start_url: str, max_pages: int = 50, schema: str = None):
    crawler = DeepCrawler(max_pages=max_pages)
    results = _run_sync(crawler.crawl(start_url))
    stored  = 0
    for r in results:
        if r.success:
            try:
                ex = _run_sync(extractor.extract(r.html, schema=schema, url=r.url))
                _run_sync(memory.store(ex.summary, {
                    "url": r.url, "domain": r.domain, "summary": ex.summary,
                    "schema_name": ex.schema_name, "scraped_at": utcnow().isoformat(),
                }))
                stored += 1
            except Exception as exc:
                log.warning("Deep crawl extraction failed %s: %s", r.url, exc)
    return {"crawled": len(results), "stored": stored, "start_url": start_url}


# =============================================================================
# §SECURITY
# =============================================================================
from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-NGAI-API-Key", auto_error=False)
_rate_store: dict[str, list] = defaultdict(list)


def verify_api_key(api_key: Optional[str] = Security(_api_key_header)) -> str:
    if not settings.API_KEYS:
        return "dev"
    if api_key not in settings.API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or missing NGAI API key")
    return api_key


async def rate_limit(request: Request) -> None:
    ip    = request.client.host if request.client else "unknown"
    now   = time.monotonic()
    limit = settings.RATE_LIMIT_PER_MINUTE
    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < 60.0]
    if len(_rate_store[ip]) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {limit} req/min",
        )
    _rate_store[ip].append(now)


# =============================================================================
# §PERFORMANCE
# =============================================================================

class ResponseCache:
    """In-memory TTL cache keyed by (namespace, query_hash)."""

    def __init__(self, ttl: int = None) -> None:
        self._ttl   = ttl or settings.CACHE_TTL_SECONDS
        self._store: dict[str, tuple[Any, float]] = {}

    def _key(self, ns: str, data: Any) -> str:
        raw = json.dumps(data, sort_keys=True, default=str)
        return f"{ns}:{hashlib.md5(raw.encode()).hexdigest()}"

    def get(self, ns: str, data: Any) -> Optional[Any]:
        entry = self._store.get(self._key(ns, data))
        if not entry:
            return None
        val, ts = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[self._key(ns, data)]
            return None
        return val

    def set(self, ns: str, data: Any, value: Any) -> None:
        self._store[self._key(ns, data)] = (value, time.monotonic())

    def invalidate(self, ns: str) -> int:
        keys = [k for k in self._store if k.startswith(f"{ns}:")]
        for k in keys:
            del self._store[k]
        return len(keys)

    @property
    def size(self) -> int:
        return len(self._store)


cache = ResponseCache()


# =============================================================================
# §API_ROUTES
# =============================================================================
from fastapi import APIRouter
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

_AUTH = [Depends(rate_limit), Depends(verify_api_key)]

# ── /ngai/search ──────────────────────────────────────────────────────────────
search_router = APIRouter(dependencies=_AUTH)


class SearchRequest(PydanticModel):
    query:  str
    top_k:  int           = 10
    live:   bool          = False
    schema: Optional[str] = None
    domain: Optional[str] = None


@search_router.post("/")
async def ngai_search(req: SearchRequest):
    cached = cache.get("search", req.dict())
    if cached:
        return {**cached, "cached": True}
    data = await search_engine.search(
        query=req.query, top_k=req.top_k,
        live=req.live, schema=req.schema, domain=req.domain,
    )
    cache.set("search", req.dict(), data)
    return data


# ── /ngai/scrape ──────────────────────────────────────────────────────────────
scrape_router = APIRouter(dependencies=_AUTH)


class ScrapeRequest(PydanticModel):
    urls:       list[str]
    schema:     Optional[str] = None
    js_render:  bool          = True
    screenshot: bool          = False
    async_job:  bool          = False
    deep_crawl: bool          = False
    max_pages:  int           = 50


@scrape_router.post("/")
async def ngai_scrape(req: ScrapeRequest, db: AsyncSession = Depends(get_db)):
    job_id = uuid.uuid4()

    if req.deep_crawl and len(req.urls) == 1:
        ct = task_deep_crawl.delay(req.urls[0], req.max_pages, req.schema)
        return {"job_id": str(job_id), "status": "queued",
                "message": f"Deep crawl queued: {ct.id}"}

    if req.async_job:
        ct  = task_scrape_urls.delay(req.urls, req.schema, req.screenshot)
        job = ScrapeJob(id=job_id, urls=req.urls, status="queued", task_id=ct.id,
                        config={"schema": req.schema, "js_render": req.js_render})
        db.add(job)
        await db.commit()
        return {"job_id": str(job_id), "status": "queued", "message": f"Job queued: {ct.id}"}

    task = AgentTask(id=str(job_id), agent="scraper",
                     input={"urls": req.urls, "schema": req.schema, "screenshot": req.screenshot})
    result = await NGAIScraperAgent().run(task)
    data   = result.result or {}
    cache.invalidate("search")
    return {"job_id": str(job_id), "status": result.status,
            "scraped": data.get("scraped", 0), "stored": data.get("stored", []),
            "failed": data.get("failed", []), "message": result.error or "Done"}


@scrape_router.get("/{job_id}")
async def ngai_scrape_status(job_id: str):
    from celery.result import AsyncResult
    r = AsyncResult(job_id, app=celery_app)
    return {"job_id": job_id, "status": r.status,
            "result": r.result if r.ready() else None}


# ── /ngai/analyze ─────────────────────────────────────────────────────────────
analyze_router = APIRouter(dependencies=_AUTH)


class AnalyzeRequest(PydanticModel):
    topic:  str
    schema: Optional[str] = None
    domain: Optional[str] = None
    top_k:  int           = 20


@analyze_router.post("/")
async def ngai_analyze(req: AnalyzeRequest):
    cached = cache.get("analyze", req.dict())
    if cached:
        return {**cached, "cached": True}
    task   = AgentTask(id=str(uuid.uuid4()), agent="analyzer",
                       input={**req.dict()})
    result = await NGAIAnalyzerAgent().run(task)
    data   = result.result or {}
    cache.set("analyze", req.dict(), data)
    return data


# ── /ngai/predict ─────────────────────────────────────────────────────────────
predict_router = APIRouter(dependencies=_AUTH)


class PredictRequest(PydanticModel):
    topic: str
    top_k: int = 30


class StartupRequest(PydanticModel):
    sector: str


class CompetitorRequest(PydanticModel):
    company: str


@predict_router.post("/")
async def ngai_predict(req: PredictRequest):
    cached = cache.get("predict", req.dict())
    if cached:
        return {**cached, "cached": True}
    data = await prediction_engine.predict(req.topic, req.top_k)
    cache.set("predict", req.dict(), data)
    return data


@predict_router.post("/startups")
async def ngai_startups(req: StartupRequest):
    return await prediction_engine.detect_startups(req.sector)


@predict_router.post("/competitor")
async def ngai_competitor(req: CompetitorRequest):
    return await prediction_engine.competitor_track(req.company)


# ── /ngai/monitor ─────────────────────────────────────────────────────────────
monitor_router = APIRouter(dependencies=_AUTH)


class MonitorCreateRequest(PydanticModel):
    name:             str
    url:              str
    interval_minutes: float = 30
    alert_on_change:  bool  = True


@monitor_router.post("/")
async def ngai_create_monitor(req: MonitorCreateRequest, db: AsyncSession = Depends(get_db)):
    mon = MonitorTarget(id=uuid.uuid4(), name=req.name, url=req.url,
                        interval_minutes=req.interval_minutes,
                        alert_on_change=req.alert_on_change, active=True)
    db.add(mon)
    await db.commit()
    await db.refresh(mon)
    return {"id": str(mon.id), "name": mon.name, "url": mon.url, "status": "active"}


@monitor_router.get("/")
async def ngai_list_monitors(db: AsyncSession = Depends(get_db)):
    result  = await db.execute(select(MonitorTarget).where(MonitorTarget.active == True))
    targets = result.scalars().all()
    return {"monitors": [
        {"id": str(m.id), "name": m.name, "url": m.url,
         "interval_minutes": m.interval_minutes,
         "last_checked": m.last_checked.isoformat() if m.last_checked else None}
        for m in targets
    ]}


@monitor_router.delete("/{monitor_id}")
async def ngai_delete_monitor(monitor_id: str, db: AsyncSession = Depends(get_db)):
    try:
        mid = uuid.UUID(monitor_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid monitor ID format")
    result = await db.execute(select(MonitorTarget).where(MonitorTarget.id == mid))
    mon    = result.scalar_one_or_none()
    if not mon:
        raise HTTPException(status_code=404, detail="Monitor not found")
    mon.active = False
    await db.commit()
    return {"status": "deactivated", "id": monitor_id}


# ── /ngai/alerts ──────────────────────────────────────────────────────────────
alerts_router = APIRouter(dependencies=_AUTH)


class AlertCheckRequest(PydanticModel):
    condition: str


@alerts_router.get("/")
async def ngai_list_alerts(
    unread_only: bool = False,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    q = select(AlertRecord).order_by(AlertRecord.fired_at.desc()).limit(limit)
    if unread_only:
        q = q.where(AlertRecord.read == False)
    result = await db.execute(q)
    alerts = result.scalars().all()
    return {"alerts": [
        {"id": str(a.id), "type": a.type, "message": a.message,
         "payload": a.payload, "fired_at": a.fired_at.isoformat(), "read": a.read}
        for a in alerts
    ], "total": len(alerts)}


@alerts_router.post("/check")
async def ngai_check_alert(req: AlertCheckRequest):
    mems = await memory.recall(req.condition, top_k=10)
    llm  = AIExtractionEngine.get_llm(AIExtractionEngine)
    for m in mems:
        raw    = await llm.ainvoke(
            f"Does this match the alert condition: '{req.condition}'?\n\n"
            f"Content: {m.get('summary','')}\n\n"
            f"Answer JSON: {{\"match\": true/false, \"reason\": \"...\"}}"
        )
        result = _parse_json_safe(raw.content)
        if result and result.get("match"):
            return {"fired": True, "condition": req.condition,
                    "matched_url": m.get("url",""), "reason": result.get("reason")}
    return {"fired": False, "condition": req.condition}


@alerts_router.patch("/{alert_id}/read")
async def ngai_mark_read(alert_id: str, db: AsyncSession = Depends(get_db)):
    try:
        aid = uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")
    await db.execute(update(AlertRecord).where(AlertRecord.id == aid).values(read=True))
    await db.commit()
    return {"status": "ok"}


# ── /ngai/agents ──────────────────────────────────────────────────────────────
agents_router = APIRouter(dependencies=_AUTH)


class AgentRunRequest(PydanticModel):
    agent: str
    input: dict


@agents_router.get("/")
async def ngai_list_agents():
    return {"agents": [
        {"name": n, "description": (c.__doc__ or "").strip().splitlines()[0]}
        for n, c in _AGENT_REGISTRY.items()
    ]}


@agents_router.post("/run")
async def ngai_run_agent(req: AgentRunRequest):
    if req.agent not in _AGENT_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unknown agent: {req.agent}")
    task   = AgentTask(id=str(uuid.uuid4()), agent=req.agent, input=req.input)
    result = await get_agent(req.agent).run(task)
    return {"task_id": task.id, "agent": req.agent, "status": result.status,
            "result": result.result, "error": result.error}


# ── /ngai/intelligence ────────────────────────────────────────────────────────
intelligence_router = APIRouter(dependencies=_AUTH)


class IntelligenceRequest(PydanticModel):
    question: str
    topics:   list[str] = []


@intelligence_router.post("/")
async def ngai_intelligence(req: IntelligenceRequest):
    cached = cache.get("intelligence", req.dict())
    if cached:
        return {**cached, "cached": True}
    topics = req.topics or req.question.split()[:5]
    task   = AgentTask(id=str(uuid.uuid4()), agent="intelligence",
                       input={"question": req.question, "topics": topics})
    result = await NGAIIntelligenceAgent().run(task)
    data   = result.result or {}
    cache.set("intelligence", req.dict(), data)
    return data


# ── /ngai/memory ──────────────────────────────────────────────────────────────
memory_router = APIRouter(dependencies=_AUTH)


@memory_router.get("/stats")
async def ngai_memory_stats():
    size = await memory.collection_size()
    return {"collection": settings.QDRANT_COLLECTION, "total_memories": size,
            "cache_entries": cache.size, "embedding_model": settings.EMBEDDING_MODEL}


@memory_router.delete("/{point_id}")
async def ngai_forget(point_id: str):
    await memory.forget(point_id)
    return {"status": "forgotten", "point_id": point_id}


# ── /ngai/trend ───────────────────────────────────────────────────────────────
trend_router = APIRouter(dependencies=_AUTH)


class TrendRequest(PydanticModel):
    query:   str
    sector:  str           = ""
    region:  str           = "global"
    top_k:   int           = 30


@trend_router.post("/")
async def ngai_detect_trends(req: TrendRequest):
    cached = cache.get("trend", req.dict())
    if cached:
        return {**cached, "cached": True}
    task   = AgentTask(id=str(uuid.uuid4()), agent="trend", input=req.dict())
    result = await NGAITrendAgent().run(task)
    if result.status == "failed":
        raise HTTPException(status_code=500, detail=result.error)
    data = result.result or {}
    cache.set("trend", req.dict(), data)
    return data


@trend_router.get("/history")
async def ngai_trend_history(db: AsyncSession = Depends(get_db), limit: int = 20):
    rows = (await db.execute(
        select(TrendRecord).order_by(TrendRecord.created_at.desc()).limit(limit)
    )).scalars().all()
    return {"records": [
        {"id": str(r.id), "query": r.query, "trends": r.trends,
         "startups": r.startups, "confidence": r.confidence,
         "created_at": r.created_at.isoformat()}
        for r in rows
    ]}


# ── /ngai/competitor ──────────────────────────────────────────────────────────
competitor_router = APIRouter(dependencies=_AUTH)


class CompetitorRequest(PydanticModel):
    company:     str
    competitors: list[str] = []
    market:      str       = ""
    top_k:       int       = 20


@competitor_router.post("/")
async def ngai_competitor_analysis(req: CompetitorRequest):
    cached = cache.get("competitor", req.dict())
    if cached:
        return {**cached, "cached": True}
    task   = AgentTask(id=str(uuid.uuid4()), agent="competitor", input=req.dict())
    result = await NGAICompetitorAgent().run(task)
    if result.status == "failed":
        raise HTTPException(status_code=500, detail=result.error)
    data = result.result or {}
    cache.set("competitor", req.dict(), data)
    return data


# ── /ngai/discovery ───────────────────────────────────────────────────────────
discovery_router = APIRouter(dependencies=_AUTH)


class DiscoveryRequest(PydanticModel):
    query:      str
    max_sites:  int            = 5
    schema:     Optional[str]  = None
    deep_crawl: bool           = False


@discovery_router.post("/")
async def ngai_auto_discover(req: DiscoveryRequest):
    task   = AgentTask(id=str(uuid.uuid4()), agent="discovery", input=req.dict())
    result = await NGAIDiscoveryAgent().run(task)
    if result.status == "failed":
        raise HTTPException(status_code=500, detail=result.error)
    return result.result


@discovery_router.get("/history")
async def ngai_discovery_history(db: AsyncSession = Depends(get_db), limit: int = 20):
    rows = (await db.execute(
        select(DiscoveryRecord).order_by(DiscoveryRecord.created_at.desc()).limit(limit)
    )).scalars().all()
    return {"records": [
        {"id": str(r.id), "query": r.query, "scraped": r.scraped_count,
         "stored": r.stored_count, "created_at": r.created_at.isoformat()}
        for r in rows
    ]}


# ── /ngai/dataset ─────────────────────────────────────────────────────────────
dataset_router = APIRouter(dependencies=_AUTH)


class DatasetBuildRequest(PydanticModel):
    action:     str            = "build"   # build | export | list | delete
    name:       Optional[str]  = None
    query:      str            = ""
    schema:     Optional[str]  = None
    top_k:      int            = 50
    format:     str            = "json"    # json | jsonl | csv | training
    dataset_id: Optional[str]  = None


@dataset_router.post("/")
async def ngai_dataset(req: DatasetBuildRequest):
    inp    = req.dict()
    task   = AgentTask(id=str(uuid.uuid4()), agent="dataset", input=inp)
    result = await NGAIDatasetAgent().run(task)
    if result.status == "failed":
        raise HTTPException(status_code=500, detail=result.error)
    return result.result


@dataset_router.get("/")
async def ngai_list_datasets(db: AsyncSession = Depends(get_db), limit: int = 20):
    rows = (await db.execute(
        select(DatasetRecord).order_by(DatasetRecord.created_at.desc()).limit(limit)
    )).scalars().all()
    return {"datasets": [
        {"id": str(r.id), "name": r.name, "rows": r.rows,
         "schema": r.schema_name, "created_at": r.created_at.isoformat()}
        for r in rows
    ]}


@dataset_router.get("/{dataset_id}")
async def ngai_get_dataset(dataset_id: str, fmt: str = "json",
                           db: AsyncSession = Depends(get_db)):
    try:
        did = uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dataset ID")
    row = (await db.execute(select(DatasetRecord).where(DatasetRecord.id == did))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    agent  = NGAIDatasetAgent()
    export = agent._format_export(row.data, fmt, row.name)
    return {"id": dataset_id, "name": row.name, "rows": row.rows, **export}


# ── /ngai/orchestrator ────────────────────────────────────────────────────────
orchestrator_router = APIRouter(dependencies=_AUTH)


class OrchestratorRequest(PydanticModel):
    goal:      str
    context:   dict = {}
    max_steps: int  = 6


@orchestrator_router.post("/")
async def ngai_orchestrate(req: OrchestratorRequest):
    task   = AgentTask(id=str(uuid.uuid4()), agent="orchestrator", input=req.dict())
    result = await NGAIOrchestratorAgent().run(task)
    if result.status == "failed":
        raise HTTPException(status_code=500, detail=result.error)
    return {"task_id": task.id, **result.result}


# =============================================================================
# §MAIN_APP
# =============================================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("=" * 60)
    log.info("NGAI — Nishal Global Artificial Intelligence")
    log.info("Ultra Extreme Internet Intelligence Engine")
    log.info("=" * 60)
    await init_db()
    await init_vector_memory()
    log.info("NGAI is operational.")
    yield
    log.info("NGAI shutting down.")


app = FastAPI(
    title="NGAI — Nishal Global Artificial Intelligence",
    description="Ultra Extreme Internet Intelligence Engine",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/ngai/docs",
    redoc_url="/ngai/redoc",
    openapi_url="/ngai/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router,       prefix="/ngai/search",       tags=["Search"])
app.include_router(scrape_router,       prefix="/ngai/scrape",       tags=["Scrape"])
app.include_router(analyze_router,      prefix="/ngai/analyze",      tags=["Analyze"])
app.include_router(predict_router,      prefix="/ngai/predict",      tags=["Predict"])
app.include_router(monitor_router,      prefix="/ngai/monitor",      tags=["Monitor"])
app.include_router(alerts_router,       prefix="/ngai/alerts",       tags=["Alerts"])
app.include_router(agents_router,       prefix="/ngai/agents",       tags=["Agents"])
app.include_router(intelligence_router, prefix="/ngai/intelligence",  tags=["Intelligence"])
app.include_router(memory_router,       prefix="/ngai/memory",       tags=["Memory"])
app.include_router(trend_router,        prefix="/ngai/trend",        tags=["Trend"])
app.include_router(competitor_router,   prefix="/ngai/competitor",   tags=["Competitor"])
app.include_router(discovery_router,    prefix="/ngai/discovery",    tags=["Discovery"])
app.include_router(dataset_router,      prefix="/ngai/dataset",      tags=["Dataset"])
app.include_router(orchestrator_router, prefix="/ngai/orchestrator", tags=["Orchestrator"])


@app.get("/ngai/health", tags=["System"])
async def ngai_health():
    mem_size = await memory.collection_size()
    return {
        "status":  "operational",
        "service": "NGAI — Nishal Global Artificial Intelligence",
        "version": "2.0.0",
        "memory":  mem_size,
        "cache":   cache.size,
        "agents":  list(_AGENT_REGISTRY.keys()),
    }


@app.get("/ngai/system", tags=["System"])
async def ngai_system():
    return {
        "name":      "NGAI",
        "full_name": "Nishal Global Artificial Intelligence",
        "version":   "2.0.0",
        "llm":       settings.DEFAULT_LLM,
        "embedding": settings.EMBEDDING_MODEL,
        "vector_db": settings.QDRANT_URL,
        "broker":    settings.REDIS_URL,
        "agents":    list(_AGENT_REGISTRY.keys()),
        "endpoints": [
            "POST /ngai/search",
            "POST /ngai/scrape",
            "GET  /ngai/scrape/{job_id}",
            "POST /ngai/analyze",
            "POST /ngai/predict",
            "POST /ngai/predict/startups",
            "POST /ngai/predict/competitor",
            "POST /ngai/monitor",
            "GET  /ngai/monitor",
            "DELETE /ngai/monitor/{id}",
            "GET  /ngai/alerts",
            "POST /ngai/alerts/check",
            "PATCH /ngai/alerts/{id}/read",
            "GET  /ngai/agents",
            "POST /ngai/agents/run",
            "POST /ngai/intelligence",
            "GET  /ngai/memory/stats",
            "DELETE /ngai/memory/{point_id}",
            # ── NEW v2 ──────────────────────────────
            "POST /ngai/trend",
            "GET  /ngai/trend/history",
            "POST /ngai/competitor",
            "POST /ngai/discovery",
            "GET  /ngai/discovery/history",
            "POST /ngai/dataset",
            "GET  /ngai/dataset",
            "GET  /ngai/dataset/{id}",
            "POST /ngai/orchestrator",
            # ── System ──────────────────────────────
            "GET  /ngai/health",
            "GET  /ngai/system",
            "GET  /ngai/docs",
        ],
    }


# =============================================================================
# §DEPLOYMENT
# Run with:
#   uvicorn ngai:app --host 0.0.0.0 --port 8000 --workers 4
#
# Celery worker:
#   celery -A ngai.celery_app worker --loglevel=info --concurrency=4
#
# Celery beat (scheduler):
#   celery -A ngai.celery_app beat --loglevel=info
#
# Required services (docker-compose.yml):
#   PostgreSQL  :5432
#   Redis       :6379
#   Qdrant      :6333
#   MinIO       :9000
#
# Required environment variables (.env):
#   DATABASE_URL, REDIS_URL, QDRANT_URL
#   MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
#   OPENROUTER_API_KEY          — get yours at https://openrouter.ai/keys
#   DEFAULT_LLM                    — any slug from https://openrouter.ai/models
#   EMBEDDING_PROVIDER             — "local" (no key) or "openai" (needs OPENAI_API_KEY)
#   API_KEYS (comma-separated, leave empty for dev)
#   ALLOWED_ORIGINS (comma-separated)
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ngai:app", host="0.0.0.0", port=8000, reload=True)
