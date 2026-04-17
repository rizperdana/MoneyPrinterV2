"""
FastAPI application factory.

Registers all routers, CORS middleware, and serves the built frontend.
"""

import os
import pathlib
import sys

# Ensure src/ is importable
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src_dir = os.path.join(_project_root, "src")
for _p in [_project_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from dotenv import load_dotenv

load_dotenv(os.path.join(_project_root, ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.routers import generate, upload, accounts, settings, oauth
from api.ws import router as ws_router

# Initialize the database on startup
from db import init_db, import_config_to_db

app = FastAPI(title="MoneyPrinterV2", version="2.0.0")


@app.on_event("startup")
async def startup():
    init_db()
    import_config_to_db()


# CORS for Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(generate.router, prefix="/api", tags=["generate"])
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(accounts.router, prefix="/api", tags=["accounts"])
app.include_router(settings.router, prefix="/api", tags=["settings"])
app.include_router(oauth.router, tags=["auth"])

# WebSocket router (no prefix — /ws/jobs/{id})
app.include_router(ws_router, tags=["websocket"])


# Serve .mp videos folder
@app.get("/.mp/{filename:path}")
async def serve_mp_video(filename: str):
    """Serve video files from .mp folder."""
    video_path = pathlib.Path(_project_root) / ".mp" / filename
    if video_path.is_file():
        return FileResponse(video_path)
    return {"detail": "Video not found"}


# Serve built frontend in production (only if web/dist exists)
_dist_dir = os.path.join(_project_root, "web", "dist")
if os.path.isdir(_dist_dir):
    from fastapi.responses import HTMLResponse

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        # Skip API routes
        if path.startswith("api") or path.startswith("ws") or path.startswith("auth"):
            return {"detail": "Not Found"}

        # Check if file exists
        file_path = os.path.join(_dist_dir, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)

        # Fallback to index.html for SPA
        index_path = os.path.join(_dist_dir, "index.html")
        return FileResponse(index_path, media_type="text/html")
