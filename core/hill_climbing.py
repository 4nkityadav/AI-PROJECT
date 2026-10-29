"""
hill_climbing.py — Hill Climbing solver (steepest-ascent with random restarts).

Used as an extra comparison point in experiments.
Like Min-Conflicts but without the random walk — always picks the
strictly best neighbour. Uses random restarts to escape local minima.
"""

from __future__ import annotations
import time
import random
import logging
from core.models import Dataset, Timetable, SolverConfig, Result
from core.csp import build_domains
from core.constraints import count_violations, count_conflicts_for_assignment

logger = logging.getLogger(__name__)


def solve_hill_climbing(dataset: Dataset, config: SolverConfig) -> Result:
    """
    Steepest-ascent hill climbing with random restarts.

    At each step, pick the conflicted session and value that give
    the largest cost reduction. If no improvement is possible, restart.
    """
    random.seed(config.seed)
    start_time = time.time()

    domains = build_domains(dataset, config)
    sessions = dataset.sessions

    best_cost = float("inf")
    best_assignment = None
    cost_history = []
    total_iterations = 0
    max_restarts = 20

    for restart in range(max_restarts):
        if time.time() - start_time > config.time_limit:
            break

        # Random initial assignment
        assignment = {}
        for session in sessions:
            domain = domains.get(session, [])
            if domain:
                assignment[session] = random.choice(domain)

        tt = Timetable(assignment=dict(assignment))
        report = count_violations(tt, dataset, config)
        current_cost = report.cost

        if current_cost < best_cost:
            best_cost = current_cost
            best_assignment = dict(assignment)

        no_improve = 0

        for iteration in range(config.max_iterations // max_restarts):
            total_iterations += 1
            if time.time() - start_time > config.time_limit:
                break

            # Find the best single-variable move
            best_delta = 0
            best_move = None  # (session, new_value)

            # Sample a subset of sessions for speed
            sample_size = min(len(sessions), 20)
            sampled = random.sample(sessions, sample_size)

            for session in sampled:
                old_val = assignment.get(session)
                if old_val is None:
                    continue

                domain = domains.get(session, [])
                # Sample domain too if it's very large
                if len(domain) > 30:
                    domain_sample = random.sample(domain, 30)
                else:
                    domain_sample = domain

                for value in domain_sample:
                    if value == old_val:
                        continue

                    # Compute cost delta by temporarily assigning
                    old_conflicts = count_conflicts_for_assignment(
                        session, old_val, assignment, dataset)
                    # Remove session temporarily to avoid self-conflict
                    saved = assignment.pop(session)
                    new_conflicts = count_conflicts_for_assignment(
                        session, value, assignment, dataset)
                    assignment[session] = saved

                    delta = new_conflicts - old_conflicts  # Negative = improvement
                    if delta < best_delta:
                        best_delta = delta
                        best_move = (session, value)

            if best_move is not None:
                session, value = best_move
                assignment[session] = value
                no_improve = 0

                # Recompute cost periodically
                if total_iterations % 50 == 0:
                    tt = Timetable(assignment=dict(assignment))
                    report = count_violations(tt, dataset, config)
                    current_cost = report.cost
                    cost_history.append(current_cost)

                    if current_cost < best_cost:
                        best_cost = current_cost
                        best_assignment = dict(assignment)

                    if report.hard_count == 0:
                        break
            else:
                no_improve += 1
                if no_improve > 50:
                    break  # Local minimum — restart

        # Check if we found a valid solution
        tt = Timetable(assignment=dict(assignment))
        report = count_violations(tt, dataset, config)
        if report.hard_count == 0 and report.cost < best_cost:
            best_cost = report.cost
            best_assignment = dict(assignment)
            break

    elapsed = time.time() - start_time

    if best_assignment is None:
        return Result(
            timetable=None, success=False,
            hard_violations=-1, soft_penalty=-1, cost=-1,
            time_seconds=elapsed, nodes_or_iterations=total_iterations,
            cost_history=cost_history, status="failed",
            algorithm="Hill Climbing",
        )

    timetable = Timetable(assignment=best_assignment)
    final_report = count_violations(timetable, dataset, config)
    cost_history.append(final_report.cost)

    return Result(
        timetable=timetable,
        success=final_report.hard_count == 0,
        hard_violations=final_report.hard_count,
        soft_penalty=final_report.soft_penalty,
        cost=final_report.cost,
        time_seconds=elapsed,
        nodes_or_iterations=total_iterations,
        cost_history=cost_history,
        status="solved" if final_report.hard_count == 0 else "failed",
        algorithm="Hill Climbing",
    )
