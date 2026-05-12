#!/usr/bin/env python3
"""Generate experiment plots for the multi-heuristic GBFS project.

Three plots are produced:
  1. Cactus plot  - coverage over time, all strategies on hFF + hLM pair
                   with hFF and hLM as individual baselines.
  2. Heatmap      - problems solved per strategy per domain.
  3. Bar chart    - coverage with runtime annotated for 2 heuristics
                   vs 3 heuristics configs.
"""

import glob
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

RESULTS_DIR = Path("experiment_results")
PLOTS_DIR = Path("plots")
PLOTS_DIR.mkdir(exist_ok=True)

DOMAINS = ["blocks", "logistics", "zenotravel", "parcprinter", "sokoban"]
MAIN_PAIR = "hff,landmark"

Q1_STYLES = {
    "hFF": ("#888780", "--", "o"),
    "hLM": ("#444441", "--", "s"),
    "Alternation (hFF, hLM)": ("#1D9E75", "-", "o"),
    "Max (hFF, hLM)": ("#185FA5", "-", "s"),
    "Sum (hFF, hLM)": ("#BA7517", "-", "^"),
    "Pareto (hFF, hLM)": ("#D4537E", "-", "D"),
}

HEATMAP_LABELS = {
    "hFF": "Single (hFF)",
    "hLM": "Single (hLM)",
    "Alternation (hFF, hLM)": "Alternation",
    "Max (hFF, hLM)": "Max",
    "Sum (hFF, hLM)": "Sum",
    "Pareto (hFF, hLM)": "Pareto",
}

Q3_CONFIGS = [
    ("Alternation (hFF, hLM)", "#1D9E75"),
    ("Alternation (hAdd, hFF, hLM)", "#0F6E56"),
    ("Max (hFF, hLM)", "#378ADD"),
    ("Max (hAdd, hFF, hLM)", "#185FA5"),
]


# Data loading


def latest(pattern: str) -> Path | None:
    files = sorted(
        glob.glob(str(RESULTS_DIR / pattern)),
        key=lambda f: Path(f).stat().st_mtime,
    )
    return Path(files[-1]) if files else None


def load_data() -> dict:
    dfs = {}

    exp1 = latest("exp1_*.csv")
    if exp1:
        df = pd.read_csv(exp1)
        dfs["hFF"] = df[df["heuristic"] == "hff"].copy()
        dfs["hLM"] = df[df["heuristic"] == "landmark"].copy()

    for key, pattern in [
        ("Alternation (hFF, hLM)", "exp2_alternation_*.csv"),
        ("Max (hFF, hLM)", "exp2_max_*.csv"),
        ("Sum (hFF, hLM)", "exp2_sum_*.csv"),
        ("Pareto (hFF, hLM)", "exp2_pareto_*.csv"),
    ]:
        path = latest(pattern)
        if path:
            df = pd.read_csv(path)
            dfs[key] = df[df["heuristics"] == MAIN_PAIR]

    exp3 = latest("exp3_*.csv")
    if exp3:
        df3 = pd.read_csv(exp3)
        dfs["Alternation (hAdd, hFF, hLM)"] = df3[df3["strategy"] == "alternation"]
        dfs["Max (hAdd, hFF, hLM)"] = df3[df3["strategy"] == "max"]

    return dfs


# Shared helper


def draw_cactus(ax, times, label, color, linestyle="-"):
    counts = list(range(1, len(times) + 1))
    ax.step(
        times,
        counts,
        where="post",
        color=color,
        linewidth=1.5,
        linestyle=linestyle,
        label=label,
    )
    ax.plot(times[-1], counts[-1], "o", color=color, markersize=5)


# Plot 1: Cactus plot - coverage over time


def plot_coverage_over_time(dfs: dict) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    endpoints = []

    for label, (color, linestyle, marker) in Q1_STYLES.items():
        df = dfs.get(label)
        if df is None:
            continue
        solved = df[df["solved"]].sort_values("time")
        if solved.empty:
            continue
        times = solved["time"].values
        counts = list(range(1, len(times) + 1))

        ax.step(
            times,
            counts,
            where="post",
            color=color,
            linewidth=0.8,
            linestyle=linestyle,
            label=label,
        )

        ax.plot(
            times[::15],
            counts[::15],
            marker=marker,
            color=color,
            markersize=5,
            linestyle="none",
            markerfacecolor="none",
            markeredgewidth=1.2,
        )

        endpoints.append((times[-1], counts[-1], str(counts[-1]), color))

    endpoints.sort(key=lambda e: e[1])
    min_gap = 3
    adjusted_y = []
    for i, (x, y, txt, col) in enumerate(endpoints):
        if i == 0:
            adjusted_y.append(y)
        else:
            prev = adjusted_y[-1]
            adjusted_y.append(max(y, prev + min_gap))
    for (x, y, txt, col), ay in zip(endpoints, adjusted_y):
        ax.annotate(
            txt,
            xy=(x, y),
            xytext=(x * 1.05, ay),
            fontsize=8,
            color=col,
            va="center",
            annotation_clip=False,
        )

    ax.set_xscale("log")
    ax.set_xlabel("Time (seconds)", fontsize=12)
    ax.set_ylabel("Problems solved", fontsize=12)
    ax.set_title("Coverage over time", fontsize=13, pad=12)
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=9, framealpha=0.9, loc="lower right")
    ax.grid(alpha=0.2, which="both")
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "coverage_over_time.png", dpi=200, bbox_inches="tight")
    plt.close()
    print("Saved coverage_over_time.png")


# Plot 2: Heatmap


def plot_heatmap(dfs: dict) -> None:
    tasks_per_domain = {}
    if "hFF" in dfs:
        for d in DOMAINS:
            tasks_per_domain[d] = int((dfs["hFF"]["domain"] == d).sum())

    rows = {}
    for key, display in HEATMAP_LABELS.items():
        df = dfs.get(key)
        if df is None:
            continue
        rows[display] = [int(df[df["domain"] == d]["solved"].sum()) for d in DOMAINS]

    matrix = pd.DataFrame(rows, index=DOMAINS).T

    annot = matrix.copy().astype(object)
    for d in DOMAINS:
        total = tasks_per_domain.get(d, "?")
        for label in matrix.index:
            annot.loc[label, d] = f"{matrix.loc[label, d]}/{total}"

    fig, ax = plt.subplots(figsize=(8, 4))
    sns.heatmap(
        matrix,
        annot=annot,
        fmt="",
        cmap="YlGn",
        linewidths=0.5,
        linecolor="white",
        ax=ax,
        cbar_kws={"label": "Problems solved"},
        vmin=0,
    )
    ax.set_title(
        "Problems solved per strategy and domain: (hFF,hLM) pair",
        fontsize=13,
        pad=12,
    )
    ax.set_xlabel("Domain", fontsize=11)
    ax.set_ylabel("Strategy", fontsize=11)
    ax.tick_params(axis="x", rotation=0)
    ax.tick_params(axis="y", rotation=0)

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "heatmap.png", dpi=200, bbox_inches="tight")
    plt.close()
    print("Saved heatmap.png")


# Plot 3: Coverage bar chart with runtime annotated


def plot_heuristic_scaling(dfs: dict) -> None:
    """Bar chart: coverage for each config, mean runtime shown on each bar."""
    labels = [label for label, _ in Q3_CONFIGS]
    colors = [color for _, color in Q3_CONFIGS]

    coverage = []
    runtimes = []
    for label, _ in Q3_CONFIGS:
        df = dfs.get(label)
        if df is not None:
            solved = df[df["solved"]]
            coverage.append(int(df["solved"].sum()))
            runtimes.append(solved["time"].mean())
        else:
            coverage.append(0)
            runtimes.append(0.0)

    fig, ax = plt.subplots(figsize=(9, 5))

    bars = ax.bar(labels, coverage, color=colors, width=0.5, zorder=3)

    for bar, cov, rt in zip(bars, coverage, runtimes):
        # Coverage value at the top of the bar
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            str(cov),
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
        )
        # Mean runtime inside the bar
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() / 2,
            f"avg {rt:.1f}s",
            ha="center",
            va="center",
            fontsize=9,
            color="white",
            fontweight="bold",
        )

    ax.set_ylabel("Problems solved (out of 143)", fontsize=12)
    ax.set_title(
        "Does adding a third heuristic improve performance?",
        fontsize=13,
        pad=12,
    )
    ax.set_ylim(0, 150)
    ax.tick_params(axis="x", labelsize=10)
    ax.grid(axis="y", alpha=0.2, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "heuristic_scaling.png", dpi=200, bbox_inches="tight")
    plt.close()
    print("Saved heuristic_scaling.png")


# Main


def main() -> None:
    dfs = load_data()
    if not dfs:
        print("No CSV files found in experiment_results/")
        sys.exit(1)

    plot_coverage_over_time(dfs)
    plot_heatmap(dfs)
    plot_heuristic_scaling(dfs)
    print(f"All plots saved to ./{PLOTS_DIR}/")


if __name__ == "__main__":
    main()
