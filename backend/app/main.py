"""TeamUp API: creates the FastAPI app, connects to the database on startup, and registers the routers."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .config import get_settings
from .db import close_pool, get_pool, open_pool, run_migrations
from .routers import projects, users

log = logging.getLogger("uvicorn.error")

# Swagger (/api/docs) groups endpoints by these tags, in this order.
TAGS = [
    {"name": "Users & Profile", "description": "Jira: Develop User Authentication and Profile API"},
    {"name": "Search & Matching", "description": "Jira: Develop Search and Matching API"},
    {"name": "Projects", "description": "Jira: Develop Project Management API"},
    {"name": "Join Requests & Invitations", "description": "Jira: Develop Join Request and Invitation API"},
    {"name": "Team Management", "description": "Jira: Develop Team Management API"},
    {"name": "Notifications", "description": "In-app notifications"},
    {"name": "Uploads", "description": "Project cover images"},
    {"name": "Admin", "description": "Moderation and platform metrics (admins only)"},
    {"name": "Health", "description": "Load balancer health check"},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    open_pool(settings.database_url)
    with get_pool().connection() as conn:
        applied = run_migrations(conn)
    if applied:
        log.info("Applied migrations: %s", ", ".join(applied))
    if settings.auth_mode == "dev":
        log.warning("AUTH_MODE=dev: test tokens like 'dev:<email>' are accepted. Never use this mode in AWS.")
    try:
        yield
    finally:
        close_pool()


def create_app() -> FastAPI:
    app = FastAPI(title="TeamUp API", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json",
                  redoc_url=None, openapi_tags=TAGS, lifespan=lifespan)

    @app.get("/api/health", tags=["Health"])
    def health():
        """Used by the load balancer: 200 when the API can reach the database."""
        try:
            with get_pool().connection(timeout=5) as conn:
                conn.execute("SELECT 1")
        except Exception:
            return JSONResponse(status_code=503, content={"status": "error", "database": "unavailable"})
        return {"status": "ok", "database": "ok"}

    # Order matters where paths overlap (e.g. /projects/filters must come before /projects/{project_id}).
    for module in (users, projects):
        app.include_router(module.router, prefix="/api")
    return app


app = create_app()
