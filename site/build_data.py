"""Generate the showcase site's data and images from the real projects.

    python3 site/build_data.py      # from the repository root

Writes site/data/*.json (project catalog, PPO replays, quant and NeuroFlow
results) and site/assets/ (compressed screenshots and the CV PDF), so every
number and replay on the site comes from the code in this repository.
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
DATA = SITE / "data"
SHOTS = SITE / "assets" / "shots"
STANDALONE = ROOT / "standalone"

sys.path.insert(0, str(ROOT))
from hub.catalog import PROFILE, PROJECTS  # noqa: E402

STANDALONE_PROJECTS = [
    {
        "slug": "neuroflow", "title": "NeuroFlow", "category": "Research",
        "summary": "When does a router that learns from delay beat shortest paths?",
        "problem": "Static shortest-path routing collapses once its busiest node saturates, while load-sensitive routing is known to oscillate.",
        "approach": "A discrete-event simulator of single-server queues, verified against M/M/1 and M/D/1 theory, compares shortest-path, load-aware distance-vector, and Q-routing across load.",
        "highlights": ["Simulator matches queueing theory within 5%", "Q-routing stays usable at 130% overload", "Distance-vector oscillation reproduced"],
        "stack": ["Python", "NumPy", "Discrete-event simulation", "Q-learning"], "path": "standalone/neuroflow",
    },
    {
        "slug": "asp-1", "title": "ASP-1", "category": "Research",
        "summary": "A power-starved deep-space probe that decides for itself when to navigate and what to send home.",
        "problem": "At 100 AU a probe wakes for two hours every 16.7 days. Each window must be split between navigation fixes and science, and the downlink cannot carry everything.",
        "approach": "A two-year mission simulator: a statistically consistent 9-state Kalman filter decides when pulsar fixes are worth their cost, a bigram model arithmetic-codes routine telemetry and flags surprises, and an eigenaxis controller slews with reaction wheels.",
        "highlights": ["Uncertainty-triggered navigation versus fixed schedules", "Lossless, model-coded downlink that flags every anomaly", "Kalman filter checked with NEES over 120 runs"],
        "stack": ["Python", "NumPy", "Kalman filtering", "Arithmetic coding"], "path": "standalone/asp-1",
    },
    {
        "slug": "mit-ocw-smart-scraper", "title": "MIT OCW Smart Scraper", "category": "Tools & web",
        "summary": "Turn an entire MIT OpenCourseWare course into one organized, searchable archive.",
        "problem": "Course material is spread across dozens of pages, videos, captions, and PDFs that are tedious to collect.",
        "approach": "Discovers courses (with a Selenium fallback for JavaScript pages), follows every section and video gallery, downloads within size limits, and merges everything into one PDF with a table of contents.",
        "highlights": ["1,110-page merged PDF from a live course", "Captions and transcripts included", "Polite rate limiting and retries"],
        "stack": ["Python", "Selenium", "BeautifulSoup", "PDF tooling"], "path": "standalone/mit-ocw-smart-scraper",
    },
    {
        "slug": "effekt-website", "title": "Effekt website", "category": "Tools & web",
        "summary": "A multilingual portfolio for bath, sauna, and pool work, introduced by interactive water.",
        "problem": "A visual business needed a fast site in three languages whose long Azerbaijani words never break badly.",
        "approach": "React and Three.js with a WebGL water introduction, responsive AVIF/WebP imagery, and syllable-based hyphenation for Azerbaijani and Russian headings.",
        "highlights": ["WebGL water introduction", "English, Azerbaijani, Russian", "Deployed on Cloudflare Workers"],
        "stack": ["React", "TypeScript", "Three.js", "Vite"], "path": "standalone/effekt-website",
    },
]


def save_shot(source: Path, slug: str) -> str | None:
    if not source.exists():
        return None
    SHOTS.mkdir(parents=True, exist_ok=True)
    image = Image.open(source).convert("RGB")
    image.thumbnail((1280, 800))
    target = SHOTS / f"{slug}.webp"
    image.save(target, "WEBP", quality=78, method=6)  # re-encoding also drops any source metadata
    return f"assets/shots/{slug}.webp"


def projects() -> list[dict]:
    items = []
    for project in PROJECTS:
        item = {key: project[key] for key in ("slug", "title", "category", "summary", "problem", "approach", "highlights", "stack", "featured", "mode")}
        item["path"] = f"projects/{project['slug']}"
        item["image"] = save_shot(ROOT / "projects" / project["slug"] / "docs" / "screenshot.png", project["slug"])
        items.append(item)
    extra_images = {
        "neuroflow": STANDALONE / "neuroflow" / "docs" / "latency_vs_load.png",
        "asp-1": STANDALONE / "asp-1" / "docs" / "navigation.png",
        "effekt-website": ROOT / "site" / "source-images" / "effekt.png",
        "mit-ocw-smart-scraper": ROOT / "site" / "source-images" / "mit-ocw.png",
    }
    for project in STANDALONE_PROJECTS:
        items.append({**project, "featured": False, "mode": "Standalone", "image": save_shot(extra_images[project["slug"]], project["slug"])})
    return items


def ppo_replays() -> dict:
    lab = ROOT / "projects" / "multitask-ppo-lab"
    sys.path.insert(0, str(lab / "src"))
    from multitask_ppo_lab.services.lab_service import LabService

    service = LabService(lab / "artifacts")
    summary = service.summary()
    replays = {}
    for task in ("navigation", "key_door"):
        episodes = []
        for seed in range(1, 60):
            oracle = service.episode(task, "oracle", seed)
            ppo = service.episode(task, "ppo_greedy", seed)
            if ppo["success"] and oracle["steps"] >= (5 if task == "navigation" else 9):
                random = service.episode(task, "random", seed)
                episodes.append({"seed": seed, "runs": {name: {key: run[key] for key in ("success", "steps", "optimal_steps", "frames", "actions")}
                                                       for name, run in (("random", random), ("ppo", ppo), ("oracle", oracle))}})
            if len(episodes) == 4:
                break
        replays[task] = episodes
    return {"evaluation": summary["evaluation"], "training": summary["training"],
            "parameters": summary["parameters"], "minutes": round(summary["training_seconds"] / 60), "replays": replays}


def quant() -> dict:
    lab = ROOT / "projects" / "quant-research-lab"
    sys.path.insert(0, str(lab / "src"))
    from quant_research_lab.domain.models import ForecastRequest, StrategyRequest
    from quant_research_lab.services.lab_service import LabService

    service = LabService()
    forecast = service.forecast(ForecastRequest(dataset_id="aapl-daily"))
    strategy = service.strategy(StrategyRequest(dataset_id="aapl-daily"))
    return {"dataset": forecast["dataset"], "evaluation": forecast["evaluation"], "scores": forecast["scores"],
            "strategy": strategy["strategy"], "buy_and_hold": strategy["buy_and_hold"],
            "equity": [{"date": row["date"], "strategy": row["strategy"], "buy_and_hold": row["buy_and_hold"]} for row in strategy["equity"]]}


def neuroflow() -> list[dict]:
    rows = list(csv.DictReader((STANDALONE / "neuroflow" / "docs" / "results.csv").open()))
    numeric = ("load", "arrival_rate", "mean_latency", "ci95", "p95_latency", "drop_rate", "mean_hops", "max_utilization")
    return [{**row, **{key: float(row[key]) for key in numeric}} for row in rows]


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    catalog = {"profile": {key: PROFILE[key] for key in ("name", "email", "github")}, "projects": projects()}
    outputs = {"projects.json": catalog, "ppo.json": ppo_replays(), "quant.json": quant(), "neuroflow.json": neuroflow()}
    for name, payload in outputs.items():
        (DATA / name).write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        print(f"wrote site/data/{name} ({(DATA / name).stat().st_size // 1024} KB)")
    cv = ROOT / "cv" / "Sanan_Shahverdi_CV.pdf"
    if cv.exists():
        shutil.copy(cv, SITE / "assets" / "Sanan_Shahverdi_CV.pdf")


if __name__ == "__main__":
    main()
