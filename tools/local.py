#!/usr/bin/env python3
"""Portable local launcher, console builder, and project test runner."""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hub.catalog import PROJECTS


def execute(command, cwd=ROOT, env=None):
    result = subprocess.run(command, cwd=cwd, env=env, check=False)
    return result.returncode


def build(install=False):
    failures = []
    for project in PROJECTS:
        folder = ROOT / "projects" / project["slug"] / "frontend"
        if not (folder / "package.json").is_file():
            if not (folder / "index.html").is_file():
                failures.append(project["slug"])
            continue
        print(f"Building {project['title']}…", flush=True)
        if install or not (folder / "node_modules").is_dir():
            if execute(["npm", "ci", "--no-audit", "--no-fund"], folder):
                failures.append(project["slug"])
                continue
        if execute(["npm", "run", "build", "--", f"--base=/demos/{project['slug']}/", "--outDir=dist-portfolio"], folder):
            failures.append(project["slug"])
    if failures:
        print("Build failed: " + ", ".join(failures), file=sys.stderr)
        return 1
    print(f"All {len(PROJECTS)} project consoles are ready.")
    return 0


def doctor():
    missing = [name for name in ["fastapi", "uvicorn", "httpx", "multipart", "bs4", "pypdf", "docx", "markdown", "numpy", "networkx", "wasmtime"] if not importlib.util.find_spec(name)]
    if missing:
        print("Missing Python dependencies: " + ", ".join(missing))
        print("Install with: python3 -m pip install -r requirements-local.txt")
    consoles = []
    for project in PROJECTS:
        folder = ROOT / "projects" / project["slug"] / "frontend"
        index = folder / "dist-portfolio/index.html" if (folder / "package.json").exists() else folder / "index.html"
        if not index.is_file():
            consoles.append(project["title"])
    print(f"Consoles ready: {len(PROJECTS) - len(consoles)}/{len(PROJECTS)}")
    if consoles:
        print("Run npm run build to prepare: " + ", ".join(consoles))
    return int(bool(missing or consoles))


def test():
    failures = []
    suites = [("hub", "Hub", ROOT)] + [
        (project["slug"], project["title"], ROOT / "projects" / project["slug"])
        for project in PROJECTS
    ]
    for slug, title, folder in suites:
        # Test fixtures can reset repositories. Never inherit live storage paths,
        # and keep each suite's persistence separate from every other suite.
        with TemporaryDirectory(prefix="portfolio-tests-") as directory:
            state = Path(directory)
            env = dict(os.environ)
            env.update(
                PYTHONPATH=str(ROOT if folder == ROOT else folder / "src"),
                PORTFOLIO_STATE_DIR=str(state),
                RAG_STATE_DIR=str(state / "rag"),
                DATA_QUALITY_STATE_FILE=str(state / "observatory.json"),
                CAPACITY_STATE_FILE=str(state / "capacity.json"),
                DELIVERY_DESK_DB=str(state / "delivery.sqlite3"),
                STOCKROOM_INVENTORY_DB=str(state / "stockroom.sqlite3"),
                AGENTIC_BA_ALLOW_REMOTE_EXPORT="false",
            )
            for name in ("GITHUB_TOKEN", "GH_TOKEN", "GITHUB_REPOSITORY", "MLFLOW_TRACKING_URI"):
                env.pop(name, None)
            print(f"Testing {title}…", flush=True)
            if execute([sys.executable, "-m", "pytest", "tests", "-q"], folder, env):
                failures.append(slug)
    print("Failed: " + ", ".join(failures) if failures else "Portfolio and all project suites passed.")
    return int(bool(failures))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["start", "build", "doctor", "test"])
    parser.add_argument("--port", type=int, default=3000)
    parser.add_argument("--install", action="store_true", help="Reinstall locked console dependencies before building")
    parser.add_argument("--reload", action="store_true", help="Reload the Python server during development")
    parser.add_argument("--no-demo", action="store_true", help="Start with empty project workspaces instead of demo data")
    args = parser.parse_args()
    if args.command == "build":
        return build(args.install)
    if args.command == "doctor":
        return doctor()
    if args.command == "test":
        return test()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    print(f"Portfolio: http://127.0.0.1:{args.port}\nAll changes stay local. Press Ctrl+C to stop.", flush=True)
    env = dict(os.environ, PORTFOLIO_DEMO_DATA="0" if args.no_demo else "1")
    return execute([sys.executable, "-m", "uvicorn", "hub.app:app", "--host", "127.0.0.1", "--port", str(args.port), *(["--reload"] if args.reload else [])], env=env)


if __name__ == "__main__":
    raise SystemExit(main())
