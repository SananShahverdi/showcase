"""Write the README results table from docs/results.csv."""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    rows = list(csv.DictReader((ROOT / "docs" / "results.csv").open()))
    agents = list(dict.fromkeys(row["agent"] for row in rows))
    loads = list(dict.fromkeys(row["load"] for row in rows))
    lookup = {(row["agent"], row["load"]): row for row in rows}
    lines = ["| Busiest-node load | " + " | ".join(agents) + " |", "|---:|" + "---:|" * len(agents)]
    for load in loads:
        cells = []
        for agent in agents:
            row = lookup[(agent, load)]
            cells.append(f"{float(row['mean_latency']):.1f} ± {float(row['ci95']):.1f} ({float(row['mean_hops']):.1f} hops)")
        lines.append(f"| {float(load):.0%} | " + " | ".join(cells) + " |")
    lines += ["", "Mean delivery time in time units with its 95% confidence interval, and mean hops per packet. "
              "One time unit is the mean service time (μ = 1); link delays are about 1."]
    readme = ROOT / "README.md"
    text = readme.read_text()
    start, end = text.index("<!-- results:start -->"), text.index("<!-- results:end -->")
    readme.write_text(text[:start] + "<!-- results:start -->\n" + "\n".join(lines) + "\n" + text[end:])
    print("\n".join(lines))


if __name__ == "__main__":
    main()
