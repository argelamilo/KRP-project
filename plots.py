#!/usr/bin/env python3
import glob
import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from pathlib import Path

RESULTS_DIR = Path("experiment_results")
PLOTS_DIR   = Path("plots")
PLOTS_DIR.mkdir(exist_ok=True)

MAIN_PAIR = "hff,landmark"
SINGLE    = "hadd"
DOMAINS   = ['blocks', 'logistics', 'zenotravel', 'parcprinter', 'sokoban']
PAIRS     = ['hff,hadd', 'hmax,lmcut', 'hff,landmark', 'landmark,lmcut']
PAIR_LABELS = {
    "hff,hadd":       "hFF + hAdd",
    "hmax,lmcut":     "hMax + LMcut",
    "hff,landmark":   "hFF + hLM",
    "landmark,lmcut": "hLM + LMcut",
}

STRATEGY_STYLE = {
    "Single (hAdd)": {"color": "#5F5E5A", "lw": 0.8, "dash": (5, 3), "zorder": 2, "marker": "o", "ms": 3},
    "Alternation":   {"color": "#1D9E75", "lw": 0.8, "dash": (),      "zorder": 5, "marker": "s", "ms": 3},
    "Max":           {"color": "#378ADD", "lw": 0.8, "dash": (4, 2),  "zorder": 4, "marker": "^", "ms": 3},
    "Sum":           {"color": "#BA7517", "lw": 0.8, "dash": (8, 3),  "zorder": 3, "marker": "D", "ms": 3},
    "Pareto":        {"color": "#D4537E", "lw": 0.8, "dash": (2, 2),  "zorder": 1, "marker": "x", "ms": 3},
}

PAIR_STYLE = {
    "hff,hadd":       {"color": "#5F5E5A", "lw": 0.8, "dash": (5, 3), "marker": "o", "ms": 3},
    "hmax,lmcut":     {"color": "#378ADD", "lw": 0.8, "dash": (4, 2), "marker": "^", "ms": 3},
    "hff,landmark":   {"color": "#1D9E75", "lw": 0.8, "dash": (),     "marker": "s", "ms": 3},
    "landmark,lmcut": {"color": "#BA7517", "lw": 0.8, "dash": (8, 3), "marker": "D", "ms": 3},
}


def latest(pattern):
    files = sorted(glob.glob(str(RESULTS_DIR / pattern)), key=lambda f: Path(f).stat().st_mtime)
    return Path(files[-1]) if files else None


def load_all():
    dfs = {}
    exp1 = latest("exp1_*.csv")
    if exp1:
        df = pd.read_csv(exp1)
        single = df[df["heuristic"] == SINGLE].copy()
        single["heuristics"] = SINGLE
        dfs["Single (hAdd)"] = single
    for label, pattern in [("Alternation", "exp2_alternation_*.csv"), ("Max", "exp2_max_*.csv"),
                            ("Sum", "exp2_sum_*.csv"), ("Pareto", "exp2_pareto_*.csv")]:
        path = latest(pattern)
        if path:
            dfs[label] = pd.read_csv(path)
    return dfs


def cactus(ax, times, label, style):
    counts = list(range(1, len(times) + 1))
    ls = (0, style["dash"]) if style["dash"] else "solid"
    ax.step(times, counts, where="post", color=style["color"], lw=style["lw"],
            linestyle=ls, zorder=style.get("zorder", 2), label=label)
    step = max(1, len(counts) // 15)
    ax.plot(times[::step], counts[::step], marker=style["marker"], color=style["color"],
            ms=style["ms"], linestyle="none", zorder=style.get("zorder", 2) + 1)
    ax.plot(times[-1], counts[-1], marker=style["marker"], color=style["color"],
            ms=style["ms"], linestyle="none", zorder=style.get("zorder", 2) + 1)
    ax.annotate(f"{counts[-1]}", xy=(times[-1], counts[-1]),
                xytext=(5, 2), textcoords="offset points",
                fontsize=9, color=style["color"], va="bottom")


def legend_handles(style_dict, keys, labels=None):
    handles = []
    for i, key in enumerate(keys):
        if key not in style_dict:
            continue
        s = style_dict[key]
        h = mlines.Line2D([], [], color=s["color"], lw=s["lw"],
                          linestyle=(0, s["dash"]) if s["dash"] else "solid",
                          marker=s["marker"], ms=s["ms"],
                          label=labels[i] if labels else key)
        handles.append(h)
    return handles


def save(ax, path, log_x=False):
    if log_x:
        ax.set_xscale("log")
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.set_xlim(0.1, 350)
        ax.grid(axis="both", alpha=0.2, lw=0.5, which="both")
    else:
        ax.grid(axis="both", alpha=0.2, lw=0.5)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()


def plot_results_hff_landmark(dfs):
    fig, ax = plt.subplots(figsize=(9, 5))
    for label, style in STRATEGY_STYLE.items():
        if label not in dfs:
            continue
        df = dfs[label]
        subset = df if label == "Single (hAdd)" else df[df["heuristics"] == MAIN_PAIR]
        solved = subset[subset["solved"] == True].sort_values("time")
        if not solved.empty:
            cactus(ax, solved["time"].values, label, style)
    ax.set_xlabel("Time (seconds, log scale)", fontsize=11)
    ax.set_ylabel("Problems solved", fontsize=11)
    ax.set_title("Multiple heuristics (hFF + hLM) vs Single (hAdd)", fontsize=12, pad=10)
    ax.set_ylim(bottom=0)
    ax.legend(handles=legend_handles(STRATEGY_STYLE, list(STRATEGY_STYLE.keys())),
              fontsize=9, framealpha=0.9, loc="upper left")
    save(ax, PLOTS_DIR / "results_hff_landmark.png", log_x=True)


def plot_results_by_pair(dfs):
    if "Alternation" not in dfs:
        return
    fig, ax = plt.subplots(figsize=(9, 5))
    for pair in PAIRS:
        style = PAIR_STYLE[pair]
        solved = dfs["Alternation"][(dfs["Alternation"]["heuristics"] == pair) &
                                    (dfs["Alternation"]["solved"] == True)].sort_values("time")
        if not solved.empty:
            cactus(ax, solved["time"].values, PAIR_LABELS[pair], style)
    ax.set_xlabel("Time (seconds, log scale)", fontsize=11)
    ax.set_ylabel("Problems solved", fontsize=11)
    ax.set_title("Results by heuristic pair (Alternation)", fontsize=12, pad=10)
    ax.set_ylim(bottom=0)
    ax.legend(handles=legend_handles(PAIR_STYLE, PAIRS, [PAIR_LABELS[p] for p in PAIRS]),
              fontsize=9, framealpha=0.9, loc="upper left")
    save(ax, PLOTS_DIR / "results_by_pair.png", log_x=True)


def plot_plan_length(dfs):
    strategies = ["Alternation", "Max", "Sum", "Pareto"]
    x = list(range(len(PAIRS)))
    width, offsets = 0.18, [-1.5, -0.5, 0.5, 1.5]
    fig, ax = plt.subplots(figsize=(9, 5))
    for label, offset in zip(strategies, offsets):
        if label not in dfs:
            continue
        means = [dfs[label][(dfs[label]["heuristics"] == p) & (dfs[label]["solved"] == True)]["plan_length"].mean()
                 for p in PAIRS]
        ax.bar([xi + offset * width for xi in x], means, width=width,
               color=STRATEGY_STYLE[label]["color"], label=label, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([PAIR_LABELS[p] for p in PAIRS], fontsize=9)
    ax.set_ylabel("Mean plan length", fontsize=11)
    ax.set_title("Plan length", fontsize=12, pad=10)
    ax.legend(fontsize=9, framealpha=0.9)
    save(ax, PLOTS_DIR / "plan_length.png")


def plot_coverage_by_domain(dfs):
    strategies = list(STRATEGY_STYLE.keys())
    width = 0.15
    x = list(range(len(DOMAINS)))
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, label in enumerate(strategies):
        if label not in dfs:
            continue
        df = dfs[label]
        counts = [int((df if label == "Single (hAdd)" else df[df["heuristics"] == MAIN_PAIR])
                      [lambda d: d["domain"] == domain]["solved"].sum())
                  for domain in DOMAINS]
        ax.bar([xi + (i - (len(strategies) - 1) / 2) * width for xi in x],
               counts, width=width, color=STRATEGY_STYLE[label]["color"], label=label, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([d.capitalize() for d in DOMAINS], fontsize=10)
    ax.set_ylabel("Problems solved", fontsize=11)
    ax.set_title("Coverage by domain (hFF + hLM vs single hAdd)", fontsize=12, pad=10)
    ax.legend(fontsize=9, framealpha=0.9)
    save(ax, PLOTS_DIR / "coverage_by_domain.png")


def plot_expansions(dfs):
    strategies = list(STRATEGY_STYLE.keys())
    means = []
    for label in strategies:
        if label not in dfs:
            means.append(0)
            continue
        df = dfs[label]
        subset = df if label == "Single (hAdd)" else df[df["heuristics"] == MAIN_PAIR]
        solved = subset[subset["solved"] == True]
        means.append(solved["expansions"].mean() if not solved.empty else 0)
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(strategies, means, color=[STRATEGY_STYLE[l]["color"] for l in strategies],
                  width=0.55, zorder=3)
    for bar, val in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 50,
                f"{int(val):,}", ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("Mean expansions", fontsize=11)
    ax.set_title("State expansions (hFF + hLM)", fontsize=12, pad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
    save(ax, PLOTS_DIR / "expansions.png")


def main():
    dfs = load_all()
    if not dfs:
        print("No CSVs found in experiment_results/")
        sys.exit(1)
    plot_results_hff_landmark(dfs)
    plot_results_by_pair(dfs)
    plot_plan_length(dfs)
    plot_coverage_by_domain(dfs)
    plot_expansions(dfs)
    print(f"Plots saved to ./{PLOTS_DIR}/")


if __name__ == "__main__":
    main()