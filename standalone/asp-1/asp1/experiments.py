"""Reproduce every number in the README.

    python -m asp1 experiments            # about 10 minutes on 8 cores
    python -m asp1 experiments --quick    # a smoke run

Writes docs/results.json, docs/*.csv, and docs/navigation.png.
"""

from __future__ import annotations

import csv
import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from . import control, mission, physics, telemetry

DOCS = Path(__file__).resolve().parents[1] / "docs"


def ci95(values) -> float:
    values = np.asarray(values, dtype=float)
    return float(1.96 * values.std(ddof=1) / np.sqrt(len(values))) if len(values) > 1 else 0.0


# --- 1. Downlink gate ------------------------------------------------------------------------

def gate_study(seeds: int, frames: int) -> list[dict]:
    thresholds = [4, 6, 8, 12, 16, 24]
    rows = []
    for threshold in thresholds:
        scores = []
        for seed in range(seeds):
            model = telemetry.train_model(seed=100 + seed)
            test = telemetry.FrameSource(np.random.default_rng(200 + seed), anomaly_rate=0.03).frames(frames)
            scores.append(telemetry.evaluate_gate(model, test, threshold))
        total = lambda name: sum(getattr(s, name) for s in scores)
        count = sum(s.frames for s in scores)
        rows.append({
            "threshold": threshold,
            "bits_per_frame_raw": total("raw_bits") / count,
            "bits_per_frame_lzw_frame": total("lzw_frame_bits") / count,
            "bits_per_frame_lzw_batch": total("lzw_batch_bits") / count,
            "bits_per_frame_word_index": total("index_bits") / count,
            "bits_per_frame_gate": total("gate_bits") / count,
            "recall_novel": float(np.mean([s.recall_novel for s in scores])),
            "recall_unusual": float(np.mean([s.recall_unusual for s in scores])),
            "false_alarm_rate": float(np.mean([s.false_alarm_rate for s in scores])),
            "lossless": all(s.lossless for s in scores),
            "frames": count,
        })
    return rows


# --- 2. Navigation scheduling ------------------------------------------------------------------

def _mission(args):
    policy, seed, simulate_slews = args
    report = mission.Mission(mission.MissionConfig(seed=seed, simulate_slews=simulate_slews), policy).run()
    return report.summary(), (report.days, report.error_km, report.sigma_km) if seed == 0 else None, report.lossless


def navigation_study(seeds: int, workers: int) -> tuple[list[dict], dict]:
    jobs = [(policy, seed, True) for policy in mission.POLICIES for seed in range(seeds)]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        outcomes = list(pool.map(_mission, jobs))
    rows, traces = [], {}
    for policy in mission.POLICIES:
        runs = [(o, t, ok) for (p, _, _), (o, t, ok) in zip(jobs, outcomes) if p == policy]
        summaries = [r[0] for r in runs]
        row = {"policy": policy, "seeds": len(runs), "lossless": all(r[2] for r in runs)}
        for key in ("mean_error_km", "p95_error_km", "max_error_km", "fixes_per_year", "science_frames_per_year",
                    "downlink_kbit_per_year", "raw_kbit_per_year", "mean_nees", "mean_slew_s"):
            values = [s[key] for s in summaries]
            row[key] = float(np.mean(values))
            row[key + "_ci95"] = ci95(values)
        row["anomalies"] = sum(s["anomalies"] for s in summaries)
        row["anomalies_flagged"] = sum(s["anomalies_flagged"] for s in summaries)
        row["false_alarms"] = sum(s["false_alarms"] for s in summaries)
        rows.append(row)
        traces[policy] = next(r[1] for r in runs if r[1] is not None)
    return rows, traces


# --- 3. Attitude slews -------------------------------------------------------------------------

def slew_study(count: int) -> dict:
    rng = np.random.default_rng(11)
    inertia = np.diag([120.0, 100.0, 80.0])
    results = []
    for _ in range(count):
        wheels = physics.ReactionWheels(physics.ReactionWheels.pyramid(), 0.2, 20.0)
        craft = physics.Spacecraft(inertia, wheels)
        craft.reset(physics.normalize(rng.normal(size=4)))
        momentum_before = craft.total_momentum_inertial()
        result = control.slew(craft, control.EigenaxisController(inertia), physics.normalize(rng.normal(size=4)))
        drift = float(np.linalg.norm(craft.total_momentum_inertial() - momentum_before))
        results.append((result, drift))
    ratios = [r.duration_s / r.lower_bound_s for r, _ in results if r.lower_bound_s > 0]
    return {
        "slews": count,
        "settled": sum(r.settled for r, _ in results),
        "mean_angle_deg": float(np.mean([r.angle_deg for r, _ in results])),
        "mean_duration_s": float(np.mean([r.duration_s for r, _ in results])),
        "mean_ratio_to_bound": float(np.mean(ratios)),
        "p95_ratio_to_bound": float(np.percentile(ratios, 95)),
        "max_final_error_deg": float(max(r.final_error_deg for r, _ in results)),
        "max_wheel_momentum_nms": float(max(r.peak_wheel_momentum for r, _ in results)),
        "max_momentum_drift_nms": float(max(d for _, d in results)),
    }


# --- Output ----------------------------------------------------------------------------------

def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot(traces: dict, path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping the plot")
        return
    fig, ax = plt.subplots(figsize=(9, 4.6), dpi=150)
    styles = {"Never": "#9aa3ad", "Every window": "#1f6f5c", "Every 2nd window": "#8fb3aa", "When 1σ > 20 km": "#c2571a"}
    for policy, color in styles.items():
        days, error, sigma = traces[policy]
        ax.plot(days, error, color=color, lw=1.6, label=f"{policy}: true error")
        if policy == "When 1σ > 20 km":
            ax.plot(days, np.array(sigma) * 3, color=color, lw=0.9, ls="--", alpha=0.8, label="When 1σ > 20 km: filter's 3σ bound")
    ax.set_yscale("log")
    ax.set_ylim(1, 3000)
    ax.set_xlabel("Mission day")
    ax.set_ylabel("Position error (km, log scale)")
    ax.set_title("True position error by navigation policy, one two-year mission", fontsize=10)
    ax.grid(alpha=0.25, which="both")
    ax.legend(fontsize=8, loc="upper left", frameon=False)
    fig.tight_layout()
    fig.savefig(path, metadata={"Software": None})
    plt.close(fig)


def plot_only(workers: int = 4) -> None:
    """Redraw the figure from seed 0, which is what the full study plots."""
    policies = ["Never", "Every window", "Every 2nd window", "When 1σ > 20 km"]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        outcomes = list(pool.map(_mission, [(p, 0, True) for p in policies]))
    plot({p: o[1] for p, o in zip(policies, outcomes)}, DOCS / "navigation.png")


def main(quick: bool = False, workers: int = 8) -> None:
    DOCS.mkdir(exist_ok=True)
    started = time.time()
    gate = gate_study(seeds=2 if quick else 5, frames=2000 if quick else 20000)
    print(f"gate study done ({time.time() - started:.0f}s)")
    nav, traces = navigation_study(seeds=2 if quick else 20, workers=workers)
    print(f"navigation study done ({time.time() - started:.0f}s)")
    slews = slew_study(10 if quick else 100)
    print(f"slew study done ({time.time() - started:.0f}s)")
    write_csv(DOCS / "gate.csv", gate)
    write_csv(DOCS / "navigation.csv", nav)
    (DOCS / "results.json").write_text(json.dumps({"gate": gate, "navigation": nav, "slews": slews}, indent=2))
    plot(traces, DOCS / "navigation.png")
    print(json.dumps(slews, indent=2))
