from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path

from app.config import settings
from app.api import raffle

app = FastAPI(
    title="Raffle Bot API",
    version=settings.API_VERSION,
    debug=settings.DEBUG
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(raffle.router, prefix="/api")

# Static files (for development and fallback)
static_path = Path("/app/static")
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    @app.get("/")
    async def serve_app():
        """Serve the Mini App index.html"""
        index_path = static_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"message": "Mini App not built yet"}

# Health check
@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "version": settings.API_VERSION
    }


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    print("=" * 50)
    print("Raffle Bot API starting...")
    print(f"Version: {settings.API_VERSION}")
    print(f"Debug mode: {settings.DEBUG}")
    print("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    print("Raffle Bot API shutting down...")
