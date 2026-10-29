"""
hybrid.py — Hybrid solver: Backtracking + Simulated Annealing.

Strategy:
  1. Use Backtracking (with heuristics) to find a feasible timetable
     (one with 0 hard constraint violations).
  2. Then use Simulated Annealing to improve soft constraint quality
     while NEVER accepting a move that introduces a hard violation.

This guarantees a valid timetable while optimising for quality.
"""

from __future__ import annotations
import time
import math
import random
import logging
from core.models import Dataset, Timetable, SolverConfig, Result
from core.backtracking import solve_backtracking
from core.csp import build_domains
from core.constraints import count_violations

logger = logging.getLogger(__name__)


def solve_hybrid(dataset: Dataset, config: SolverConfig) -> Result:
    """
    Hybrid: Backtracking produces feasible → SA improves soft quality.
    """
    random.seed(config.seed)
    start_time = time.time()

    # Phase 1: Get a feasible solution via backtracking with heuristics
    bt_config = SolverConfig(
        seed=config.seed,
        time_limit=config.time_limit / 2,  # Use half the time budget
        max_nodes=config.max_nodes,
        use_mrv=True, use_degree=True,
        use_forward_checking=True,
        use_lcv=False, use_ac3=False,
        lab_block_size=config.lab_block_size,
        lab_mode=config.lab_mode,
        weight_s1=config.weight_s1, weight_s2=config.weight_s2,
        weight_s3=config.weight_s3, weight_s4=config.weight_s4,
        weight_s5=config.weight_s5,
    )

    bt_result = solve_backtracking(dataset, bt_config)

    if not bt_result.success or bt_result.timetable is None:
        logger.warning("Backtracking failed in hybrid — returning its result as-is")
        bt_result.algorithm = "Hybrid (BT failed)"
        bt_result.time_seconds = time.time() - start_time
        return bt_result

    logger.info("Phase 1 (Backtracking) done: hard=%d, soft=%.1f",
                bt_result.hard_violations, bt_result.soft_penalty)

    # Phase 2: SA improvement (no hard violations allowed)
    from core.constraints import FastOccupancy
    assignment = dict(bt_result.timetable.assignment)
    domains = build_domains(dataset, config)
    sessions = dataset.sessions

    occ = FastOccupancy()
    for s, val in assignment.items():
        if val is not None:
            occ.add(s, val[0], val[1], val[2])

    report = count_violations(Timetable(assignment=dict(assignment)), dataset, config)
    current_cost = report.soft_penalty
    best_cost = current_cost
    best_assignment = dict(assignment)
    initial_soft = current_cost

    cost_history = [bt_result.cost]
    temp = config.sa_initial_temp / 2
    iteration = 0
    no_improve = 0

    while temp > config.sa_min_temp:
        if time.time() - start_time > config.time_limit or best_cost == 0 or no_improve > 250:
            break

        for _ in range(config.sa_iterations_per_temp):
            iteration += 1

            s = random.choice(sessions)
            domain = domains.get(s, [])
            if not domain:
                continue

            old_val = assignment[s]
            new_val = random.choice(domain)
            if new_val == old_val:
                continue

            # Fast O(1) hard constraint check
            occ.remove(s, old_val[0], old_val[1], old_val[2])
            if occ.count_conflicts(s, new_val[0], new_val[1], new_val[2], dataset) > 0:
                occ.add(s, old_val[0], old_val[1], old_val[2])
                continue

            # Move is valid (0 hard violations)
            assignment[s] = new_val
            occ.add(s, new_val[0], new_val[1], new_val[2])

            new_tt = Timetable(assignment=dict(assignment))
            new_report = count_violations(new_tt, dataset, config)
            new_soft = new_report.soft_penalty
            delta = new_soft - current_cost

            if delta <= 0:
                current_cost = new_soft
                if new_soft < best_cost:
                    best_cost = new_soft
                    best_assignment = dict(assignment)
                    no_improve = 0
            elif temp > 0 and random.random() < math.exp(-delta / max(temp, 0.001)):
                current_cost = new_soft
            else:
                occ.remove(s, new_val[0], new_val[1], new_val[2])
                assignment[s] = old_val
                occ.add(s, old_val[0], old_val[1], old_val[2])

            if iteration % 100 == 0:
                cost_history.append(new_report.cost)

        temp *= config.sa_cooling_alpha
        no_improve += 1

    elapsed = time.time() - start_time

    # Final evaluation
    timetable = Timetable(assignment=best_assignment)
    final_report = count_violations(timetable, dataset, config)
    cost_history.append(final_report.cost)

    logger.info("Phase 2 (SA) done: soft improved from %.1f to %.1f in %.3fs",
                initial_soft, final_report.soft_penalty, elapsed)

    return Result(
        timetable=timetable,
        success=final_report.hard_count == 0,
        hard_violations=final_report.hard_count,
        soft_penalty=final_report.soft_penalty,
        cost=final_report.cost,
        time_seconds=elapsed,
        nodes_or_iterations=bt_result.nodes_or_iterations + iteration,
        cost_history=cost_history,
        status="solved" if final_report.hard_count == 0 else "failed",
        algorithm="Hybrid (BT+SA)",
        metadata={
            "bt_nodes": bt_result.nodes_or_iterations,
            "sa_iterations": iteration,
            "soft_improvement": initial_soft - final_report.soft_penalty,
        },
    )
