from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import Base, engine
from .routers import admin, public


settings = get_settings()
Base.metadata.create_all(bind=engine)


def _ensure_sqlite_schema() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as connection:
        columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(lessons)").fetchall()
        }
        if "lesson_layout" not in columns:
            connection.exec_driver_sql("ALTER TABLE lessons ADD COLUMN lesson_layout JSON")


_ensure_sqlite_schema()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(public.router)

settings.upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


@app.get("/api/health")
def healthcheck() -> dict:
    return {"status": "ok"}


frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str) -> FileResponse:
        file_path = (frontend_dist / full_path).resolve()
        if file_path.is_relative_to(frontend_dist) and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
