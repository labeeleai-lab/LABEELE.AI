"""
app_factory.py - create_app(): builds the FastAPI instance, CORS, the
/assets StaticFiles mount, includes every router, and finally runs the
duplicate-route startup guard.

Transitional note (Step 8 of the modularization plan): at this point no
routers have been extracted into coordinator_API/routers/ yet, so
create_app() includes none and _assert_no_duplicate_routes() only sees the
handful of routes FastAPI registers itself (docs/openapi/redoc). Real route
handlers still live inline in coordinator_api.py, decorated directly onto
the `app` instance this function returns - both styles coexist fine during
the transition. As each router is extracted in Step 9, an
`app.include_router(...)` call is added here and the matching inline routes
are deleted from coordinator_api.py, so the guard's real coverage grows
with each step until, by Step 10, every route is guarded.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from coordinator_API.core.config import ASSETS_DIR
from coordinator_API.lifespan import lifespan
from coordinator_API.routers import (
    health, agency_tools, admin_dashboard, admin_knowledge, admin_training,
    admin_personas, iac, agents, auth, tasks,
)


def _assert_no_duplicate_routes(app: FastAPI) -> None:
    """
    Raises at startup if two routers (or two inline route definitions)
    silently register the same (method, path) pair - the exact bug class
    that produced the 3 confirmed duplicate routes found in the original
    monolith (GET /tasks, POST /admin/clear-cache, POST /admin/retrain-agents).
    Turns silent shadowing into a hard failure, permanently, going forward.
    """
    seen = {}
    for route in app.routes:
        if not hasattr(route, "methods"):
            continue
        for method in route.methods:
            key = (method, route.path)
            if key in seen:
                raise RuntimeError(f"Duplicate route: {method} {route.path} (already in {seen[key]})")
            seen[key] = route.endpoint.__module__


def create_app() -> FastAPI:
    app = FastAPI(title="AICP Coordinator", lifespan=lifespan)

    # ==================== CORS CONFIGURATION (FIXED) ====================
    # Define all trusted origins (Local + Production)
    origins = [
        "http://localhost:3000",                # Your local frontend (React)
        "http://127.0.0.1:3000",                # Alternate local address
        "https://www.labeele.ai",               # Your production domain
        "https://labeele.ai",                   # Root domain
        "https://labeele-ai-web.vercel.app",    # Vercel deployments
        "https://huggingface.co",               # Hugging Face internal calls
        "*"                                     # TEMPORARY: Allow all to ensure it works
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,   # Use the list above
        allow_credentials=True,
        allow_methods=["*"],     # Allow all methods (GET, POST, OPTIONS, etc.)
        allow_headers=["*"],     # Allow all headers (Authorization, etc.)
    )
    # ====================================================================

    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

    # ==================== ROUTERS ====================
    # (extracted incrementally in Step 9)
    app.include_router(health.router)
    app.include_router(agency_tools.router)
    app.include_router(admin_dashboard.router)
    app.include_router(admin_knowledge.router)
    app.include_router(admin_training.router)
    app.include_router(admin_personas.router)
    app.include_router(iac.router)
    app.include_router(agents.router)
    app.include_router(auth.router)
    app.include_router(tasks.router)

    _assert_no_duplicate_routes(app)
    return app
