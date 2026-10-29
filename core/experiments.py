"""
experiments.py — Run comparison experiments across all algorithms.

Produces:
  - Comparison table (CSV) with time, nodes/iterations, hard violations,
    soft penalty, success rate
  - Ablation table for backtracking heuristics
  - Cost vs iterations graphs
  - Scalability graphs
  - Auto-drafted analysis text

Can be run from the UI or CLI:
  python -m core.experiments --dataset both --runs 10 --out results/
"""

from __future__ import annotations
import os
import time
import random
import logging
import argparse
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

from core.models import Dataset, SolverConfig, Result
from core.loader import load_json, parse_dataset
from core.teacher_assign import assign_teachers_and_create_sessions
from core.backtracking import solve_backtracking
from core.min_conflicts import solve_min_conflicts
from core.annealing import solve_simulated_annealing
from core.hybrid import solve_hybrid
from core.hill_climbing import solve_hill_climbing

logger = logging.getLogger(__name__)

# ── Chart styling (earthy palette, no default blue) ──
CHART_COLORS = ["#1F4D3F", "#B8582B", "#6B8E6B", "#8B6B4A", "#4A6B8B", "#8B4A6B"]
CHART_BG = "#FBF9F4"
CHART_GRID = "#D9D3C5"
CHART_TEXT = "#1E1E1C"


def _setup_chart_style():
    """Set matplotlib style to match our earthy palette."""
    plt.rcParams.update({
        "figure.facecolor": CHART_BG,
        "axes.facecolor": CHART_BG,
        "axes.edgecolor": CHART_GRID,
        "axes.labelcolor": CHART_TEXT,
        "text.color": CHART_TEXT,
        "xtick.color": CHART_TEXT,
        "ytick.color": CHART_TEXT,
        "grid.color": CHART_GRID,
        "grid.alpha": 0.5,
        "font.size": 10,
    })


SOLVERS = {
    "BT (Plain)": lambda ds, cfg: solve_backtracking(ds, SolverConfig(
        seed=cfg.seed, time_limit=cfg.time_limit, max_nodes=cfg.max_nodes,
        use_mrv=False, use_degree=False, use_lcv=False,
        use_forward_checking=False, use_ac3=False,
        lab_block_size=cfg.lab_block_size, lab_mode=cfg.lab_mode,
        weight_s1=cfg.weight_s1, weight_s2=cfg.weight_s2,
        weight_s3=cfg.weight_s3, weight_s4=cfg.weight_s4, weight_s5=cfg.weight_s5,
    )),
    "BT (Heuristics)": lambda ds, cfg: solve_backtracking(ds, cfg),
    "Min-Conflicts": lambda ds, cfg: solve_min_conflicts(ds, cfg),
    "Simulated Annealing": lambda ds, cfg: solve_simulated_annealing(ds, cfg),
    "Hybrid (BT+SA)": lambda ds, cfg: solve_hybrid(ds, cfg),
    "Hill Climbing": lambda ds, cfg: solve_hill_climbing(ds, cfg),
}

# Deterministic algorithms that only need 1 run
DETERMINISTIC = {"BT (Plain)", "BT (Heuristics)"}


def _notify_progress(callback, fraction: float, msg: str = ""):
    """Safely notify progress callback with fraction and optional status message."""
    if not callback:
        return
    try:
        callback(fraction, msg)
    except TypeError:
        try:
            callback(fraction)
        except Exception:
            pass


def run_experiments(
    dataset: Dataset,
    dataset_name: str = "dataset",
    num_runs: int = 10,
    output_dir: str = "results",
    config: SolverConfig | None = None,
    progress_callback=None,
    selected_algorithms: list[str] | None = None,
    run_ablation: bool = True,
) -> dict:
    """
    Run all algorithms and collect results.

    Returns a dict with:
      "comparison_df": DataFrame with the main comparison table
      "ablation_df": DataFrame with heuristic ablation results
      "cost_histories": dict of algorithm -> list of cost histories
      "results": dict of algorithm -> list of Result objects
    """
    if config is None:
        config = SolverConfig()

    os.makedirs(output_dir, exist_ok=True)
    _setup_chart_style()

    algos = selected_algorithms or list(SOLVERS.keys())
    all_results: dict[str, list[Result]] = {}
    cost_histories: dict[str, list[list[float]]] = {}

    total_tasks = sum(
        1 if name in DETERMINISTIC else num_runs
        for name in algos
    )
    if run_ablation:
        total_tasks += 7  # 7 ablation configs
    done = 0

    _notify_progress(progress_callback, 0.0, "Starting benchmark suite…")

    for algo_name in algos:
        if algo_name not in SOLVERS:
            continue

        solver_fn = SOLVERS[algo_name]
        runs = 1 if algo_name in DETERMINISTIC else num_runs
        results = []

        for run in range(runs):
            _notify_progress(
                progress_callback,
                done / total_tasks,
                f"Running {algo_name} (run {run + 1}/{runs})…",
            )

            run_config = SolverConfig(
                seed=run * 42 + 7,
                time_limit=config.time_limit,
                max_nodes=config.max_nodes,
                max_iterations=config.max_iterations,
                use_mrv=config.use_mrv, use_degree=config.use_degree,
                use_lcv=config.use_lcv,
                use_forward_checking=config.use_forward_checking,
                use_ac3=config.use_ac3,
                random_walk_prob=config.random_walk_prob,
                restart_after=config.restart_after,
                sa_initial_temp=config.sa_initial_temp,
                sa_cooling_alpha=config.sa_cooling_alpha,
                sa_iterations_per_temp=config.sa_iterations_per_temp,
                sa_min_temp=config.sa_min_temp,
                lab_block_size=config.lab_block_size,
                lab_mode=config.lab_mode,
                weight_s1=config.weight_s1, weight_s2=config.weight_s2,
                weight_s3=config.weight_s3, weight_s4=config.weight_s4,
                weight_s5=config.weight_s5,
            )

            try:
                result = solver_fn(dataset, run_config)
            except Exception as e:
                logger.error("Algorithm %s run %d failed: %s", algo_name, run, e)
                result = Result(
                    timetable=None, success=False,
                    hard_violations=-1, soft_penalty=-1, cost=-1,
                    time_seconds=0, nodes_or_iterations=0,
                    status="error", algorithm=algo_name,
                )

            results.append(result)
            done += 1

            _notify_progress(
                progress_callback,
                done / total_tasks,
                f"Completed {algo_name} run {run + 1}/{runs}",
            )

        all_results[algo_name] = results
        # Capture cost history, falling back to [result.cost] if empty
        cost_histories[algo_name] = [
            (r.cost_history if (r.cost_history and len(r.cost_history) > 0) else [r.cost])
            for r in results if r.cost >= 0
        ]

    # Build comparison table
    comparison_rows = []
    for algo_name, results in all_results.items():
        successful = [r for r in results if r.success]
        times = [r.time_seconds for r in results]
        nodes = [r.nodes_or_iterations for r in results]
        hard_vals = [r.hard_violations for r in results if r.hard_violations >= 0]
        soft_vals = [r.soft_penalty for r in results if r.soft_penalty >= 0]

        comparison_rows.append({
            "Algorithm": algo_name,
            "Avg Time (s)": f"{np.mean(times):.4f}" if times else "N/A",
            "Avg Nodes/Iter": f"{np.mean(nodes):.0f}" if nodes else "N/A",
            "Avg Hard Violations": f"{np.mean(hard_vals):.1f}" if hard_vals else "N/A",
            "Avg Soft Penalty": f"{np.mean(soft_vals):.1f}" if soft_vals else "N/A",
            "Success Rate": f"{len(successful)}/{len(results)}",
            "Min Time": f"{min(times):.4f}" if times else "N/A",
            "Max Time": f"{max(times):.4f}" if times else "N/A",
            "Status": results[0].status if len(results) == 1 else "mixed",
        })

    comparison_df = pd.DataFrame(comparison_rows)

    # Save comparison table
    csv_path = os.path.join(output_dir, f"comparison_{dataset_name}.csv")
    comparison_df.to_csv(csv_path, index=False)

    # Generate cost vs iterations graph
    _plot_cost_histories(cost_histories, output_dir, dataset_name)

    # Generate comparison bar chart
    _plot_comparison_bars(comparison_df, output_dir, dataset_name)

    # Run ablation study (skipped for quick compare to save time)
    if run_ablation:
        ablation_df = _run_ablation(
            dataset, config, output_dir, dataset_name,
            progress_callback=progress_callback,
            done_offset=done,
            total_tasks=total_tasks,
        )
        done += 7
        _notify_progress(progress_callback, 0.98, "Generating report analysis…")
        _generate_analysis(comparison_df, ablation_df, output_dir, dataset_name)
    else:
        ablation_df = None
        _notify_progress(progress_callback, 0.98, "Finalizing results…")

    _notify_progress(progress_callback, 1.0, "Experiments finished successfully!")

    return {
        "comparison_df": comparison_df,
        "ablation_df": ablation_df,
        "cost_histories": cost_histories,
        "results": all_results,
    }


def _plot_cost_histories(cost_histories: dict, output_dir: str, dataset_name: str):
    """Plot cost vs iterations for all algorithms.

    - Local search algorithms show convergence trajectories.
    - Single-step or constructive solvers (like BT) show horizontal reference lines.
    - Uses symlog Y-axis so SA's initial ~20000 cost doesn't squash lower-cost algorithms.
    """
    _setup_chart_style()
    fig, ax = plt.subplots(figsize=(11, 5.5))

    color_idx = 0
    has_data = False
    max_cost = 0
    max_x = 1

    # Find max length among multi-point histories
    for histories in cost_histories.values():
        for h in histories:
            if h and len(h) > max_x:
                max_x = len(h) - 1

    for algo_name, histories in cost_histories.items():
        if not histories:
            continue
        history = histories[0]
        if not history:
            continue

        has_data = True
        c = CHART_COLORS[color_idx % len(CHART_COLORS)]
        max_cost = max(max_cost, max(history))

        if len(history) <= 2:
            # Single / two point: draw a horizontal reference line and a marker at x=0
            val = history[0]
            ax.axhline(val, color=c, linestyle="--", linewidth=1.5, alpha=0.8,
                       label=f"{algo_name} (final: {val:.0f})")
            ax.scatter([0], [val], color=c, s=100, zorder=5, marker="D", edgecolors="white", linewidths=0.5)
        else:
            x = list(range(len(history)))
            ax.plot(x, history, label=f"{algo_name} (final: {history[-1]:.0f})",
                    color=c, linewidth=2, alpha=0.85)
            ax.scatter([x[0], x[-1]], [history[0], history[-1]],
                       color=c, s=40, zorder=5, edgecolors="white", linewidths=0.5)

        color_idx += 1

    if not has_data:
        plt.close(fig)
        return

    ax.set_xlim(left=-max(max_x * 0.03, 0.5), right=max(max_x * 1.05, 5))

    if max_cost > 500:
        ax.set_yscale("symlog", linthresh=100)
        ax.set_ylabel("Cost (symlog scale: 1000×hard + soft)")
        ax.set_ylim(bottom=0)
    else:
        ax.set_ylabel("Cost (1000×hard + soft)")
        ax.set_ylim(bottom=0, top=max(max_cost * 1.15, 10))

    ax.set_xlabel("Iteration (×100)")
    ax.set_title(f"Cost Convergence & Solution Quality — {dataset_name}", fontsize=13, fontweight="bold")
    ax.legend(frameon=True, fancybox=True, framealpha=0.85, fontsize=9, loc="upper right")
    ax.grid(True, alpha=0.3)

    path = os.path.join(output_dir, f"cost_iterations_{dataset_name}.png")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor=CHART_BG)
    plt.close(fig)
    logger.info("Saved cost history plot: %s", path)


def _plot_comparison_bars(comparison_df: pd.DataFrame, output_dir: str, dataset_name: str):
    """Plot bar charts comparing algorithms.

    Ensures y-axis begins at 0 on all plots and labels appear neatly.
    """
    _setup_chart_style()
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2))

    algos = comparison_df["Algorithm"].tolist()
    x = range(len(algos))
    bar_colors = CHART_COLORS[:len(algos)]

    # Time comparison
    times = []
    for t in comparison_df["Avg Time (s)"]:
        try:
            times.append(float(t))
        except (ValueError, TypeError):
            times.append(0)
    axes[0].bar(x, times, color=bar_colors, edgecolor="white", linewidth=0.5)
    axes[0].set_title("Average Time (s)", fontweight="bold")
    axes[0].set_xticks(list(x))
    axes[0].set_xticklabels(algos, rotation=45, ha="right", fontsize=8)
    max_time = max(times) if times else 1.0
    axes[0].set_ylim(bottom=0, top=max(max_time * 1.15, 0.05))
    for i, v in enumerate(times):
        if v > 0:
            axes[0].text(i, v + max_time * 0.02, f"{v:.3f}", ha="center", va="bottom", fontsize=7)

    # Hard violations
    hards = []
    for h in comparison_df["Avg Hard Violations"]:
        try:
            hards.append(float(h))
        except (ValueError, TypeError):
            hards.append(0)
    axes[1].bar(x, hards, color=bar_colors, edgecolor="white", linewidth=0.5)
    axes[1].set_title("Avg Hard Violations", fontweight="bold")
    axes[1].set_xticks(list(x))
    axes[1].set_xticklabels(algos, rotation=45, ha="right", fontsize=8)
    max_hard = max(hards) if hards else 0.0
    axes[1].set_ylim(bottom=0, top=max(max_hard * 1.2, 1.0))
    for i, v in enumerate(hards):
        axes[1].text(i, v + 0.03, f"{v:.1f}", ha="center", va="bottom", fontsize=7)

    # Soft penalties
    softs = []
    for s in comparison_df["Avg Soft Penalty"]:
        try:
            softs.append(float(s))
        except (ValueError, TypeError):
            softs.append(0)
    axes[2].bar(x, softs, color=bar_colors, edgecolor="white", linewidth=0.5)
    axes[2].set_title("Avg Soft Penalty", fontweight="bold")
    axes[2].set_xticks(list(x))
    axes[2].set_xticklabels(algos, rotation=45, ha="right", fontsize=8)
    max_soft = max(softs) if softs else 10.0
    axes[2].set_ylim(bottom=0, top=max(max_soft * 1.15, 10.0))
    for i, v in enumerate(softs):
        if v > 0:
            axes[2].text(i, v + max_soft * 0.02, f"{v:.0f}", ha="center", va="bottom", fontsize=7)

    fig.suptitle(f"Algorithm Comparison — {dataset_name}", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    path = os.path.join(output_dir, f"comparison_{dataset_name}.png")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor=CHART_BG)
    plt.close(fig)
    logger.info("Saved comparison chart: %s", path)


def _run_ablation(
    dataset: Dataset,
    config: SolverConfig,
    output_dir: str,
    dataset_name: str,
    progress_callback=None,
    done_offset: int = 0,
    total_tasks: int = 1,
) -> pd.DataFrame:
    """
    Run heuristic ablation study: Backtracking with different heuristic combinations.
    Shows which heuristic contributes most.
    """
    ablation_configs = [
        ("Plain", False, False, False, False, False),
        ("MRV only", True, False, False, False, False),
        ("FC only", False, False, False, True, False),
        ("MRV+FC", True, False, False, True, False),
        ("MRV+FC+Degree", True, True, False, True, False),
        ("MRV+FC+Degree+LCV", True, True, True, True, False),
        ("All + AC3", True, True, True, True, True),
    ]

    rows = []
    for idx, (name, mrv, deg, lcv, fc, ac3) in enumerate(ablation_configs):
        if progress_callback:
            _notify_progress(
                progress_callback,
                (done_offset + idx) / total_tasks,
                f"Ablation study: {name} ({idx + 1}/{len(ablation_configs)})…",
            )
        cfg = SolverConfig(
            seed=42,
            time_limit=min(config.time_limit, 5.0),
            max_nodes=min(config.max_nodes, 5000),
            use_mrv=mrv, use_degree=deg, use_lcv=lcv,
            use_forward_checking=fc, use_ac3=ac3,
            lab_block_size=config.lab_block_size, lab_mode=config.lab_mode,
        )
        try:
            result = solve_backtracking(dataset, cfg)
            rows.append({
                "Configuration": name,
                "Time (s)": f"{result.time_seconds:.4f}",
                "Nodes": result.nodes_or_iterations,
                "Hard Violations": result.hard_violations,
                "Soft Penalty": f"{result.soft_penalty:.1f}" if result.soft_penalty >= 0 else "N/A",
                "Status": result.status,
            })
        except Exception as e:
            logger.error("Ablation %s failed: %s", name, e)
            rows.append({
                "Configuration": name,
                "Time (s)": "error",
                "Nodes": 0,
                "Hard Violations": -1,
                "Soft Penalty": "N/A",
                "Status": "error",
            })

    ablation_df = pd.DataFrame(rows)
    csv_path = os.path.join(output_dir, f"ablation_{dataset_name}.csv")
    ablation_df.to_csv(csv_path, index=False)
    logger.info("Saved ablation results: %s", csv_path)
    return ablation_df


def _generate_analysis(comparison_df: pd.DataFrame, ablation_df: pd.DataFrame,
                       output_dir: str, dataset_name: str):
    """Generate auto-drafted analysis markdown from real experimental data."""
    lines = [
        f"# Experimental Analysis — {dataset_name}",
        "",
        "## Comparison Table",
        "",
        comparison_df.to_markdown(index=False),
        "",
        "## Heuristic Ablation (Backtracking)",
        "",
        ablation_df.to_markdown(index=False) if ablation_df is not None else "N/A",
        "",
        "## Analysis (DRAFT — rewrite in your own words)",
        "",
    ]

    # Auto-generate insights from real numbers
    try:
        # Find fastest
        times = {}
        for _, row in comparison_df.iterrows():
            try:
                times[row["Algorithm"]] = float(row["Avg Time (s)"])
            except (ValueError, TypeError):
                pass
        if times:
            fastest = min(times, key=times.get)
            slowest = max(times, key=times.get)
            lines.append(f"- **Fastest method**: {fastest} ({times[fastest]:.4f}s average)")
            lines.append(f"- **Slowest method**: {slowest} ({times[slowest]:.4f}s average)")

        # Find best soft quality
        softs = {}
        for _, row in comparison_df.iterrows():
            try:
                softs[row["Algorithm"]] = float(row["Avg Soft Penalty"])
            except (ValueError, TypeError):
                pass
        if softs:
            best_soft = min(softs, key=softs.get)
            lines.append(f"- **Best soft-constraint quality**: {best_soft} (penalty={softs[best_soft]:.1f})")

        lines.extend([
            "",
            "### When to use each method:",
            "- **Backtracking (Plain)**: Good for understanding; may be slow on large instances.",
            "- **Backtracking (Heuristics)**: Best for guaranteed solutions on moderate-sized problems.",
            "- **Min-Conflicts**: Fast for finding any valid solution; quality varies across runs.",
            "- **Simulated Annealing**: Good balance of quality and flexibility; tune parameters carefully.",
            "- **Hybrid (BT+SA)**: Best overall quality — guarantees feasibility while optimising soft constraints.",
            "- **Hill Climbing**: Simple but often gets stuck in local minima; useful as a baseline.",
            "",
            "*Note: This analysis is auto-generated from experimental data. Rewrite in your own words for the report.*",
        ])
    except Exception:
        lines.append("(Auto-analysis could not be generated — fill manually from the data above)")

    path = os.path.join(output_dir, f"analysis_{dataset_name}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info("Saved analysis: %s", path)


# ── CLI entry point ──

def main():
    parser = argparse.ArgumentParser(description="Run timetable scheduler experiments")
    parser.add_argument("--dataset", choices=["small", "large", "both"], default="both")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--out", default="results")
    parser.add_argument("--time-limit", type=float, default=60.0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    datasets = []
    if args.dataset in ("small", "both"):
        datasets.append(("small", "data/small.json"))
    if args.dataset in ("large", "both"):
        datasets.append(("large", "data/large.json"))

    config = SolverConfig(time_limit=args.time_limit)

    for name, path in datasets:
        print(f"\n{'='*60}")
        print(f"Running experiments on {name} dataset")
        print(f"{'='*60}")

        raw = load_json(path)
        dataset = parse_dataset(raw)
        assign_teachers_and_create_sessions(dataset, config)

        results = run_experiments(
            dataset, name, args.runs, args.out, config,
            progress_callback=lambda p: print(f"  Progress: {p*100:.0f}%")
        )

        print(f"\nResults for {name}:")
        print(results["comparison_df"].to_string(index=False))

    print(f"\nAll results saved to {args.out}/")


if __name__ == "__main__":
    main()
