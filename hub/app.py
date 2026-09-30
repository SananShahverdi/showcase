"""One loopback server for the portfolio and its independently testable products."""
import asyncio
import importlib
import logging
import os
from pathlib import Path
import sys

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator

from hub.catalog import BY_SLUG, PROFILE, PROJECTS
from hub.store import Store

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
logger = logging.getLogger("hub")


class SavedProject(BaseModel):
    model_config = ConfigDict(extra="forbid")
    saved: bool


class Note(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    message: str = Field(min_length=10, max_length=3000)

    @field_validator("name", "message")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Enter a value, not only spaces")
        return value


def create_app(state_dir=None, mount_projects=True):
    """Create the hub; existing project apps are shared module singletons.

    Set storage environment variables before importing this module to isolate a
    complete workspace. Separate workspaces require separate server processes;
    state_dir alone selects hub storage and defaults for first-imported projects.
    """
    state = Path(state_dir or os.environ.get("PORTFOLIO_STATE_DIR", ROOT / ".local"))
    store = Store(state / "portfolio.sqlite3")
    application = FastAPI(title="Sanan Shahverdi · Portfolio", version="1.0.0",
                          description="Local portfolio, project catalog, and persistent workspace notes.")
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"])
    mounted, failures = {}, {}

    @application.middleware("http")
    async def local_boundary(request: Request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin != f"{request.url.scheme}://{request.headers.get('host', '')}":
                return JSONResponse({"detail": "Use this workspace from its own local address."}, status_code=403)
            if request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse({"detail": "Cross-site changes are not allowed."}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    def get_project(slug):
        if slug not in BY_SLUG:
            raise HTTPException(404, "Project not found")
        return BY_SLUG[slug]

    def public_project(item):
        return {key: value for key, value in item.items() if key != "module"} | {
            "available": item["slug"] in mounted,
            "console_ready": (console_dir(item["slug"]) / "index.html").is_file(),
        }

    @application.get("/health")
    def health():
        return {"status": "ok", "projects_loaded": len(mounted), "projects_total": len(PROJECTS), "mode": "local"}

    @application.get("/api/profile")
    def profile():
        return PROFILE

    @application.get("/api/projects")
    def catalog():
        return {"projects": [public_project(item) for item in PROJECTS], "saved": store.saved()}

    @application.get("/api/status")
    async def status():
        async def check(slug, child):
            try:
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=child), base_url="http://localhost") as client:
                    response = await asyncio.wait_for(client.get("/health"), timeout=5)
                return slug, {"status": "ready" if response.status_code == 200 else "error", "console_ready": (console_dir(slug) / "index.html").is_file()}
            except Exception:
                logger.exception("Project health check failed: %s", slug)
                return slug, {"status": "error", "console_ready": (console_dir(slug) / "index.html").is_file()}
        entries = dict(await asyncio.gather(*(check(slug, child) for slug, child in mounted.items())))
        entries.update({slug: {"status": "unavailable", "console_ready": (console_dir(slug) / "index.html").is_file()} for slug in failures})
        return {"mode": "local", "projects": entries}

    @application.get("/api/projects/{slug}")
    def detail(slug: str):
        return public_project(get_project(slug))

    @application.put("/api/saved/{slug}")
    def save_project(slug: str, body: SavedProject):
        get_project(slug)
        store.save(slug, body.saved)
        return {"saved": store.saved()}

    @application.get("/api/notes")
    def notes():
        return store.notes()

    @application.post("/api/notes", status_code=201)
    def add_note(body: Note):
        return store.add_note(body.name, body.email, body.message)

    @application.get("/api/projects/{slug}/readme")
    def readme(slug: str):
        get_project(slug)
        path = ROOT / "projects" / slug / "README.md"
        if not path.is_file():
            raise HTTPException(404, "Project documentation is not available")
        return {"content": path.read_text(), "path": f"projects/{slug}/README.md"}

    def source_files(slug):
        get_project(slug)
        base = ROOT / "projects" / slug
        allowed = {".py", ".tsx", ".ts", ".js", ".css", ".md", ".html"}
        paths = []
        for folder in ["src", "tests", "frontend/src", "docs"]:
            for path in sorted((base / folder).rglob("*")):
                if path.is_file() and path.suffix in allowed and not path.is_symlink() and path.resolve().is_relative_to(base.resolve()):
                    paths.append(path.relative_to(base).as_posix())
        # The two small applications use unbundled, same-origin browser modules.
        for filename in ["frontend/app.js", "frontend/styles.css", "frontend/style.css", "frontend/index.html"]:
            path = base / filename
            if path.is_file() and not path.is_symlink():
                paths.append(filename)
        return paths[:250]

    @application.get("/api/projects/{slug}/files")
    def files(slug: str):
        return {"files": source_files(slug)}

    @application.get("/api/projects/{slug}/source")
    def source(slug: str, path: str):
        if path not in source_files(slug):
            raise HTTPException(404, "Source file not found")
        file = ROOT / "projects" / slug / path
        if file.stat().st_size > 256_000:
            raise HTTPException(413, "File is too large for the source viewer")
        return {"path": path, "content": file.read_text()}

    if mount_projects:
        os.environ.setdefault("RAG_STATE_DIR", str(state / "rag"))
        os.environ.setdefault("DATA_QUALITY_STATE_FILE", str(state / "observatory.json"))
        os.environ.setdefault("CAPACITY_STATE_FILE", str(state / "capacity.json"))
        os.environ.setdefault("DELIVERY_DESK_DB", str(state / "delivery.sqlite3"))
        os.environ.setdefault("STOCKROOM_INVENTORY_DB", str(state / "stockroom.sqlite3"))
        for item in PROJECTS:
            slug = item["slug"]
            src = str(ROOT / "projects" / slug / "src")
            if src not in sys.path:
                sys.path.insert(0, src)
            try:
                child = importlib.import_module(f"{item['module']}.api.app").app
                application.mount(f"/api/projects/{slug}", child)
                mounted[slug] = child
            except Exception as exc:
                failures[slug] = type(exc).__name__
                logger.exception("Could not load %s. Install requirements-local.txt and check the project.", slug)

    if os.environ.get("PORTFOLIO_DEMO_DATA") == "1":
        from hub.demo import seed_demos

        @application.on_event("startup")
        async def load_demo_data():
            application.state.demo_outcomes = await seed_demos(mounted)

    @application.get("/demos/{slug}")
    def demo_redirect(slug: str):
        get_project(slug)
        return RedirectResponse(f"/demos/{slug}/")

    @application.get("/demos/{slug}/{path:path}")
    def demo(slug: str, path: str):
        get_project(slug)
        base = console_dir(slug).resolve()
        if not (base / "index.html").is_file():
            raise HTTPException(503, "Build the project consoles with npm run build, then reload this page.")
        target = (base / (path or "index.html")).resolve()
        if not target.is_relative_to(base) or not target.is_file():
            raise HTTPException(404, "Console asset not found")
        return FileResponse(target)

    application.mount("/assets", StaticFiles(directory=WEB), name="assets")

    @application.get("/", include_in_schema=False)
    @application.get("/projects/{slug}", include_in_schema=False)
    def home(slug: str | None = None):
        if slug:
            get_project(slug)
        return FileResponse(WEB / "index.html")

    application.state.store = store
    application.state.projects = mounted
    application.state.failures = failures
    return application


def console_dir(slug):
    base = ROOT / "projects" / slug / "frontend"
    return base / "dist-portfolio" if (base / "package.json").exists() else base


app = create_app()
