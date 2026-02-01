"""FastAPI application instance and configuration."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.src.database import init_db

logger = logging.getLogger(__name__)

# Static files directory (built frontend)
STATIC_DIR = Path(__file__).parent.parent.parent.parent / "static"


def preload_spacy_model():
    """Pre-load spaCy model to avoid cold start on first request."""
    try:
        import spacy

        # Load en_core_web_lg - Presidio's default model for best accuracy
        logger.info("Loading spaCy model en_core_web_lg...")
        spacy.load("en_core_web_lg")
        logger.info("spaCy model loaded successfully")
    except Exception as e:
        logger.warning(f"Failed to preload spaCy model: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - runs on startup and shutdown."""
    # Startup: Initialize database
    init_db()

    # Preload spaCy model to avoid slow first request
    preload_spacy_model()

    yield
    # Shutdown: Nothing to clean up


app = FastAPI(
    title="PII Anonymizer API",
    description=(
        "Offline PII detection and anonymization service using Microsoft Presidio. "
        "Provides consistent substitution - the same PII value always maps to the same substitute."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware for frontend access (development mode)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",
        "http://localhost:8000",  # Same origin
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register API routes
from backend.src.api.routes.anonymize import router as anonymize_router  # noqa: E402
from backend.src.api.routes.config import router as config_router  # noqa: E402
from backend.src.api.routes.health import router as health_router  # noqa: E402
from backend.src.api.routes.mappings import router as mappings_router  # noqa: E402
from backend.src.api.routes.stats import router as stats_router  # noqa: E402

app.include_router(health_router, tags=["Health"])
app.include_router(anonymize_router, tags=["Anonymization"])
app.include_router(config_router, tags=["Configuration"])
app.include_router(stats_router, tags=["Statistics"])
app.include_router(mappings_router, tags=["Mappings"])


# Serve static frontend files if they exist
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/", response_class=HTMLResponse)
    async def serve_root():
        """Serve the frontend application."""
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/{path:path}")
    async def serve_spa(request: Request, path: str):
        """Serve static files or fallback to index.html for SPA routing."""
        # Skip API routes
        if path.startswith(("health", "anonymize", "config", "stats", "mappings", "docs", "openapi")):
            return None

        file_path = STATIC_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)

        # Fallback to index.html for SPA routing
        return FileResponse(STATIC_DIR / "index.html")
