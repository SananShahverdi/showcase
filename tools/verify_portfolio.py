#!/usr/bin/env python3
"""Verify the full-viable portfolio workspaces without requiring Docker.

Backend behavior and frontend compilation have dedicated test commands. This
static verifier checks the evidence they leave behind: structure, documentation,
Compose syntax, non-starter product UIs, and build output.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - environment fallback
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
PROJECTS_ROOT = ROOT / "projects"
REPORT_ROOT = PROJECTS_ROOT / "verification"

REQUIRED_PROJECT_FILES = [
    "README.md",
    "BACKLOG.md",
    ".env.example",
    "docker-compose.yml",
    "docs/architecture.md",
    "docs/algorithms-and-data-structures.md",
    "docs/testing-strategy.md",
    "docs/demo-script.md",
    "docs/adr/0001-core-architecture.md",
    "src/README.md",
    "tests/README.md",
]

REQUIRED_ROOT_FILES = [
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "LICENSE",
    ".gitignore",
    ".editorconfig",
    ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/product-improvement.md",
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/research-task.md",
]


@dataclass
class Check:
    name: str
    status: str
    detail: str


@dataclass
class ProjectResult:
    slug: str
    status: str
    checks: list[Check]


def check_ok(name: str, detail: str) -> Check:
    return Check(name=name, status="pass", detail=detail)


def check_fail(name: str, detail: str) -> Check:
    return Check(name=name, status="fail", detail=detail)


def project_dirs() -> list[Path]:
    return sorted(
        path
        for path in PROJECTS_ROOT.iterdir()
        if path.is_dir() and not path.name.startswith(".") and (path / "README.md").exists()
    )


def has_balanced_fences(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    return text.count("```") % 2 == 0


def has_mermaid(path: Path) -> bool:
    return "```mermaid" in path.read_text(encoding="utf-8")


def parse_compose(path: Path) -> tuple[bool, str]:
    if yaml is None:
        return False, "PyYAML is not installed."
    try:
        data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - report exact parser failure
        return False, f"YAML parse failed: {exc}"
    if not isinstance(data, dict):
        return False, "Compose file did not parse to a mapping."
    services = data.get("services")
    if not isinstance(services, dict) or "api" not in services or "frontend" not in services:
        return False, "Compose file must define API and frontend services."
    return True, "Compose YAML parsed with API and frontend services; optional dependencies are project-specific."


def smoke_serve_directory(path: Path) -> tuple[bool, str]:
    frontend = path / "frontend"
    if not (frontend / "package.json").exists():
        # Build-free consoles ship static HTML and browser modules served as-is.
        index, script = frontend / "index.html", frontend / "app.js"
        if not index.exists() or not script.exists():
            return False, "Static frontend requires frontend/index.html and frontend/app.js."
        if not re.search(r'<script[^>]+src="(\./)?app\.js"', index.read_text(encoding="utf-8")):
            return False, "frontend/index.html does not load app.js."
        return True, "Static browser console (no build step) with index.html and app.js."
    app_source = frontend / "src" / "App.tsx"
    build_index = path / "frontend" / "dist" / "index.html"
    assets = list((path / "frontend" / "dist" / "assets").glob("*")) if build_index.exists() else []
    if not app_source.exists():
        return False, "frontend/src/App.tsx is missing."
    source = app_source.read_text(encoding="utf-8")
    starter_markers = ("Get started", "Count is", "viteLogo")
    if any(marker in source for marker in starter_markers):
        return False, "Frontend still contains Vite starter UI markers."
    if not build_index.exists() or not assets:
        return False, "Frontend production build artifact is missing; run npm run build."
    return True, f"Product UI source is non-starter and production build contains {len(assets)} asset(s)."


def verify_project(path: Path) -> ProjectResult:
    checks: list[Check] = []

    missing = [rel for rel in REQUIRED_PROJECT_FILES if not (path / rel).exists()]
    if missing:
        checks.append(check_fail("required-files", f"Missing: {', '.join(missing)}"))
    else:
        checks.append(check_ok("required-files", "All required project files exist."))

    markdown_files = sorted(path.rglob("*.md"))
    unbalanced = [str(md.relative_to(path)) for md in markdown_files if not has_balanced_fences(md)]
    if unbalanced:
        checks.append(check_fail("markdown-fences", f"Unbalanced fences: {', '.join(unbalanced)}"))
    else:
        checks.append(check_ok("markdown-fences", f"{len(markdown_files)} Markdown files have balanced fences."))

    architecture = path / "docs" / "architecture.md"
    algorithms = path / "docs" / "algorithms-and-data-structures.md"
    if architecture.exists() and algorithms.exists() and has_mermaid(architecture) and algorithms.stat().st_size > 300:
        checks.append(check_ok("architecture-evidence", "Architecture includes Mermaid and algorithm documentation is substantive."))
    else:
        checks.append(check_fail("architecture-evidence", "Expected a Mermaid architecture and substantive algorithm documentation."))

    compose_ok, compose_detail = parse_compose(path / "docker-compose.yml")
    checks.append(check_ok("compose-yaml", compose_detail) if compose_ok else check_fail("compose-yaml", compose_detail))

    smoke_ok, smoke_detail = smoke_serve_directory(path)
    checks.append(check_ok("frontend-build", smoke_detail) if smoke_ok else check_fail("frontend-build", smoke_detail))

    unit_tests = list((path / "tests" / "unit").glob("test_*.py"))
    integration_tests = list((path / "tests" / "integration").glob("test_*.py"))
    if unit_tests and integration_tests:
        checks.append(check_ok("test-suites", f"Found {len(unit_tests)} unit and {len(integration_tests)} integration test module(s)."))
    else:
        checks.append(check_fail("test-suites", "Both unit and integration test modules are required."))

    status = "pass" if all(check.status == "pass" for check in checks) else "fail"
    return ProjectResult(slug=path.name, status=status, checks=checks)


def verify_root() -> list[Check]:
    checks: list[Check] = []
    missing = [rel for rel in REQUIRED_ROOT_FILES if not (PROJECTS_ROOT / rel).exists()]
    if missing:
        checks.append(check_fail("root-required-files", f"Missing: {', '.join(missing)}"))
    else:
        checks.append(check_ok("root-required-files", "All shared OSS files exist."))

    return checks


def markdown_report(root_checks: list[Check], projects: list[ProjectResult]) -> str:
    total_checks = len(root_checks) + sum(len(project.checks) for project in projects)
    failed_checks = sum(check.status == "fail" for check in root_checks)
    failed_checks += sum(check.status == "fail" for project in projects for check in project.checks)
    passed_projects = sum(project.status == "pass" for project in projects)

    lines = [
        "# Portfolio Verification Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Summary",
        "",
        f"- Projects verified: {len(projects)}",
        f"- Projects passed: {passed_projects}",
        f"- Total checks: {total_checks}",
        f"- Failed checks: {failed_checks}",
        f"- Docker validation: not required by this verifier; Compose YAML syntax is parsed locally.",
        "",
        "## Root Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in root_checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")

    lines.extend(
        [
            "",
            "## Project Checks",
            "",
            "| Project | Status | Checks |",
            "|---|---|---|",
        ]
    )
    for project in projects:
        details = "<br>".join(f"{check.status}: {check.name}" for check in project.checks)
        lines.append(f"| `{project.slug}` | {project.status} | {details} |")

    lines.extend(["", "## Detailed Failures", ""])
    failures = [
        (project.slug, check)
        for project in projects
        for check in project.checks
        if check.status == "fail"
    ]
    failures.extend(("root", check) for check in root_checks if check.status == "fail")
    if failures:
        for owner, check in failures:
            lines.append(f"- `{owner}` `{check.name}`: {check.detail}")
    else:
        lines.append("- None.")

    return "\n".join(lines) + "\n"


def main() -> int:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)

    root_checks = verify_root()
    projects = [verify_project(path) for path in project_dirs()]

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "root_checks": [asdict(check) for check in root_checks],
        "projects": [asdict(project) for project in projects],
    }

    (REPORT_ROOT / "portfolio_verification_report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    (REPORT_ROOT / "portfolio_verification_report.md").write_text(
        markdown_report(root_checks, projects),
        encoding="utf-8",
    )

    failed = any(check.status == "fail" for check in root_checks)
    failed = failed or any(project.status == "fail" for project in projects)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
