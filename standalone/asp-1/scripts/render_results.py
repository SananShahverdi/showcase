"""Write the README result tables from docs/results.json."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(text: str, name: str, lines: list[str]) -> str:
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    head, rest = text.split(start)
    _, tail = rest.split(end)
    return head + start + "\n" + "\n".join(lines) + "\n" + end + tail


def main() -> None:
    results = json.loads((ROOT / "docs" / "results.json").read_text())
    nav = results["navigation"]
    seeds = nav[0]["seeds"]
    navigation = [
        "| Policy | Fixes per year | Mean error (km) | 95th-percentile error (km) | Science frames per year | Mean NEES |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in nav:
        navigation.append(
            f"| {row['policy']} | {row['fixes_per_year']:.1f} | {row['mean_error_km']:.0f} ± {row['mean_error_km_ci95']:.0f} "
            f"| {row['p95_error_km']:.0f} ± {row['p95_error_km_ci95']:.0f} | {row['science_frames_per_year']:,.0f} | {row['mean_nees']:.1f} |")
    navigation += ["", f"Means over {seeds} seeded two-year missions with 95% confidence intervals. Every policy faces the same trajectories, "
                       "burns, and frames. A consistent 9-state filter has a mean NEES near 9; lower means its reported uncertainty is cautious."]

    gate = [
        "| Threshold | Gate (bits/frame) | Word indices | LZW per frame | LZW whole window | Raw text | Novel anomalies flagged | Unusual combinations flagged | False alarms |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in results["gate"]:
        gate.append(
            f"| {row['threshold']} | **{row['bits_per_frame_gate']:.1f}** | {row['bits_per_frame_word_index']:.1f} | {row['bits_per_frame_lzw_frame']:.1f} "
            f"| {row['bits_per_frame_lzw_batch']:.1f} | {row['bits_per_frame_raw']:.1f} | {row['recall_novel']:.0%} | {row['recall_unusual']:.0%} | {row['false_alarm_rate']:.2%} |")
    frames = results["gate"][0]["frames"]
    gate += ["", f"{frames:,} held-out frames (3% anomalies) against models trained only on routine frames; every frame decoded exactly."]

    s = results["slews"]
    slews = [
        f"- {s['settled']} of {s['slews']} random slews (mean {s['mean_angle_deg']:.0f}°) settled within 0.05° and 0.01°/s, "
        f"in {s['mean_duration_s']:.0f} s on average: {s['mean_ratio_to_bound']:.2f}× the bang-bang lower bound "
        f"(95th percentile {s['p95_ratio_to_bound']:.2f}×).",
        f"- Peak wheel momentum {s['max_wheel_momentum_nms']:.1f} N·m·s of the 20 available; total angular momentum "
        f"drifted by at most {s['max_momentum_drift_nms']:.0e} N·m·s.",
    ]
    readme = ROOT / "README.md"
    text = readme.read_text()
    for name, lines in (("navigation", navigation), ("gate", gate), ("slews", slews)):
        text = replace(text, name, lines)
    readme.write_text(text)
    print("README updated")


if __name__ == "__main__":
    main()
