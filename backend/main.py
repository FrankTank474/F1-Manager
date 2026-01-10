from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .api.health import router as health_router
from .api.v1.router import api_router
from .datastore.factory import create_datastore
from .dependencies import set_datastore


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: Initialize datastore
    datastore = create_datastore()
    await datastore.initialize()
    set_datastore(datastore)

    yield

    # Shutdown: Close datastore
    await datastore.close()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)

# API routes
app.include_router(health_router, prefix="/api")
app.include_router(api_router, prefix="/api/v1")

# Frontend paths
frontend_path = Path(__file__).parent.parent / "frontend"


# Serve static files if frontend directory exists
if frontend_path.exists():
    app.mount("/css", StaticFiles(directory=frontend_path / "css"), name="css")
    app.mount("/js", StaticFiles(directory=frontend_path / "js"), name="js")

    # Serve components and pages as static files
    if (frontend_path / "components").exists():
        app.mount(
            "/components",
            StaticFiles(directory=frontend_path / "components"),
            name="components",
        )
    if (frontend_path / "pages").exists():
        app.mount(
            "/pages", StaticFiles(directory=frontend_path / "pages"), name="pages"
        )


@app.get("/")
async def serve_index():
    """Serve the main frontend page."""
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "F1 Manager API", "docs": "/docs"}


@app.get("/{path:path}")
async def serve_spa(path: str):
    """Catch-all for SPA routing - serve index.html for non-API/static routes."""
    # Don't intercept API routes
    if path.startswith("api/"):
        return {"error": "Not found"}

    # Try to serve static file first
    file_path = frontend_path / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)

    # Fall back to index.html for SPA routing
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    return {"error": "Not found"}
