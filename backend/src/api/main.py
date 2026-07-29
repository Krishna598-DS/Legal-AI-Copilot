"""
FastAPI product backend + built-in web UI (free single-service deploy).

Run from repo root:
  PYTHONPATH=backend uvicorn src.api.main:app --host 0.0.0.0 --port 8010
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import account, admin, auth, chat, documents, health, orgs, professionals
from src.config import get_settings, validate_settings
from src.db.database import init_db
from src.errors import register_exception_handlers
from src.logging_config import logger
from src.observability.events import log_event
from src.observability.middleware import RequestLoggingMiddleware
from src.services import rag_service

settings = get_settings()
WEB_DIR = Path(settings.FRONTEND_DIR)


def _init_sentry() -> None:
    if not settings.SENTRY_DSN:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1,
            environment=settings.ENVIRONMENT,
        )
        logger.info("Sentry initialized")
    except Exception as exc:
        logger.warning("Sentry init failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_settings(settings)
    _init_sentry()
    init_db()
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY is not set — Q&A will fail until configured")
    else:
        try:
            rag_service.get_embeddings_model()
            rag_service.get_llm()
            logger.info("AI models warmed successfully")
        except Exception as exc:
            logger.exception("Model warmup failed: %s", exc)
    log_event(
        logger,
        "startup",
        message="API started",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )
    yield
    log_event(logger, "shutdown", message="API shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Multi-user RAG API for private legal document analysis. "
        "Not legal advice."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
)
register_exception_handlers(app)

# Allow same-origin UI and common local ports
origins = list(settings.CORS_ORIGINS)
for extra in (
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8010",
    "http://127.0.0.1:8010",
):
    if extra not in origins:
        origins.append(extra)

# Same-origin UI needs no CORS; wildcards cannot use credentials
_cors = [o for o in origins if o != "*"]
_allow_all = "*" in settings.CORS_ORIGINS or not _cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else _cors,
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Outermost: request_id + access logging
app.add_middleware(RequestLoggingMiddleware)


def _resolve_static_asset(cleaned_path: str) -> Path | None:
    """Resolve a cleaned (no leading/trailing slash) path against WEB_DIR, returning
    the file if it exists and is safely contained. Shared by the reserved-asset
    middleware below and the SPA catch-all so the path-traversal containment check
    only lives in one place."""
    if not WEB_DIR.is_dir():
        return None
    web_root = WEB_DIR.resolve()
    candidate = (web_root / cleaned_path).resolve()
    if candidate.is_relative_to(web_root) and candidate.is_file():
        return candidate
    return None


@app.middleware("http")
async def serve_reserved_static_assets(request, call_next):
    """Let Next.js's own per-route sidecar files (index.txt, fetched by the client
    router to prefetch RSC data for a page) reach the filesystem before any API
    router gets a look at them.

    Confirmed root cause of a real bug: any router with a bare `/{id}`-shaped route
    under the same path prefix as a frontend page — e.g. documents.py's
    `GET /{document_id}` under the `/documents/` page — matches `/documents/index.txt`
    by treating "index.txt" as the id, and since that request is the browser's own
    background prefetch (not our api() client, which is the only thing that attaches
    the Bearer token), it has no Authorization header and 401s. That looked like
    "every protected request fails after login" in the Network tab, when the real
    API calls were succeeding the whole time — only this one background, harmless
    prefetch was being wrongly routed and rejected.
    """
    if request.method == "GET" and request.url.path.endswith(("/index.txt", "/index.html")):
        asset = _resolve_static_asset(request.url.path.strip("/"))
        if asset is not None:
            return FileResponse(asset)
    return await call_next(request)


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(account.router)
app.include_router(orgs.router)
app.include_router(professionals.router)
app.include_router(admin.router)

if WEB_DIR.is_dir():
    # Next.js static export assets
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
    next_assets = WEB_DIR / "_next"
    if next_assets.is_dir():
        app.mount("/_next", StaticFiles(directory=str(next_assets)), name="next_static")


@app.get("/api")
def api_info():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "live": "/live",
        "ui": "/",
        "disclaimer": "/account/disclaimer",
        "privacy": "/account/privacy",
        "terms_version": settings.TERMS_VERSION,
    }


@app.get("/")
def serve_ui():
    index = WEB_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return api_info()


@app.get("/favicon.ico")
def favicon():
    icon = WEB_DIR / "favicon.ico"
    if icon.is_file():
        return FileResponse(icon)
    return api_info()


# Next.js static-export deep links (Home / Documents / Workspace / Settings / Auth).
# Registered last so API routes always win. Serves folder index.html when present.
@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    if not WEB_DIR.is_dir():
        return api_info()
    web_root = WEB_DIR.resolve()
    index = web_root / "index.html"
    cleaned = full_path.strip("/")
    if not cleaned:
        return FileResponse(index) if index.is_file() else api_info()

    # full_path is attacker-controlled and "../" segments survive `strip("/")`
    # untouched, so an unresolved join (WEB_DIR / cleaned) would let a request like
    # "/../../etc/passwd" read any file the process can access — _resolve_static_asset
    # resolves and confirms containment before ever returning a path.
    candidate = _resolve_static_asset(cleaned)
    if candidate is not None:
        return FileResponse(candidate)
    nested = _resolve_static_asset(f"{cleaned}/index.html")
    if nested is not None:
        return FileResponse(nested)

    # Client-side app shell fallback for unknown UI paths
    if index.is_file():
        return FileResponse(index)
    return api_info()
