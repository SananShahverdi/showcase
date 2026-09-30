"""Write the results section of README.md from artifacts/evaluation.json and history.json."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = {"random": "Random", "ppo_sampled": "PPO (sampled)", "ppo_greedy": "PPO (greedy)", "oracle": "Optimal (BFS)"}
TASKS = {"navigation": "Navigation", "key_door": "Key and door"}


def pct(value):
    return "—" if value is None else f"{value * 100:.1f}%"


def render() -> str:
    """The README results section, built only from the saved artifacts."""
    evaluation = json.loads((ROOT / "artifacts/evaluation.json").read_text())
    history = json.loads((ROOT / "artifacts/history.json").read_text())
    checkpoint = __import__("torch").load(ROOT / "artifacts/policy.pt", map_location="cpu", weights_only=True)
    config = checkpoint["training"]
    steps = history[-1]["env_steps"]
    minutes = history[-1]["seconds"] / 60
    lines = [
        "## Results",
        "",
        f"Trained for {config['updates']} updates ({steps:,} environment steps across both tasks, {minutes:.0f} minutes on CPU). "
        f"Evaluated on {evaluation[0]['episodes']} held-out layouts per task and policy:",
        "",
        "| Task | Policy | Success | Mean steps | Optimality | Mean return |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in evaluation:
        lines.append(f"| {TASKS[row['task']]} | {NAMES[row['policy']]} | {pct(row['success_rate'])} | {row['mean_steps']:.1f} | "
                     f"{pct(row['optimality'])} | {row['mean_return']:.2f} |")
    lines += ["", "Optimality is the optimal step count divided by the steps taken, averaged over successful episodes. "
              "Greedy play follows the optimal path whenever it succeeds, but can repeat the same action forever in a state "
              "where the policy is unsure; sampling breaks those loops, which is why it solves more layouts at slightly lower optimality.", ""]
    return "\n".join(lines)


def readme_section(text: str) -> str:
    start, end = text.index("<!-- results:start -->"), text.index("<!-- results:end -->")
    return text[start + len("<!-- results:start -->\n"):end]


def main() -> None:
    section = render()
    readme = ROOT / "README.md"
    text = readme.read_text()
    start, end = text.index("<!-- results:start -->"), text.index("<!-- results:end -->")
    readme.write_text(text[:start] + "<!-- results:start -->\n" + section + text[end:])
    print(section)


if __name__ == "__main__":
    main()
