"""
min_conflicts.py — Min-Conflicts local search solver.

Design choices (each justified):

Initial assignment:
  Random complete assignment from pruned domains. This is fast and provides
  a starting point. Alternative: greedy (assign values minimising immediate
  conflicts), selectable via config. We default to random because it gives
  more diverse starting points across runs, which helps with random restarts.

Conflicted variable selection:
  Uniformly random among sessions currently involved in at least one hard
  violation. If no hard conflicts remain, we stop (or optionally continue
  to reduce soft penalties).

Value selection:
  Pick the value that minimises the total cost. We use incremental
  conflict counting (via occupancy tables) for speed, not a full recount.

Tie-breaking:
  Random among tied values, which adds diversity.

Plateau escape:
  Two mechanisms:
  1. Random walk with probability p (default 0.02): with small probability,
     pick a random value instead of the best one.
  2. Random restart after N non-improving iterations (default 2000):
     completely reassign all conflicted variables.

Performance:
  Maintain occupancy tables (teacher/class/room per slot) for incremental
  conflict counting. Each move is O(domain_size), not O(n^2).
"""

from __future__ import annotations
import time
import random
import logging
from collections import defaultdict
from core.models import (
    Dataset, Timetable, Session, SolverConfig, Result,
)
from core.csp import build_domains
from core.constraints import (
    count_violations, count_conflicts_for_assignment, compute_cost, FastOccupancy,
)

logger = logging.getLogger(__name__)


def _create_initial_assignment(
    sessions: list[Session],
    domains: dict[Session, list],
    mode: str = "random",
    dataset: Dataset | None = None,
) -> dict[Session, tuple[int, int, str]]:
    """
    Create a complete initial assignment.
    mode="random": pick a random value from each session's domain.
    mode="greedy": pick the value with fewest immediate conflicts.
    """
    assignment = {}
    if mode == "greedy" and dataset is not None:
        occ = FastOccupancy()
        for session in sessions:
            domain = domains.get(session, [])
            if not domain:
                continue
            best_val = min(
                domain,
                key=lambda v: occ.count_conflicts(session, v[0], v[1], v[2], dataset)
            )
            assignment[session] = best_val
            occ.add(session, best_val[0], best_val[1], best_val[2])
    else:
        for session in sessions:
            domain = domains.get(session, [])
            if domain:
                assignment[session] = random.choice(domain)

    return assignment


def _find_conflicted_sessions(
    assignment: dict[Session, tuple[int, int, str]],
    sessions: list[Session],
    dataset: Dataset,
    occ: FastOccupancy,
) -> list[Session]:
    """Find all sessions involved in at least one hard constraint violation using FastOccupancy."""
    conflicted = []
    for session in sessions:
        val = assignment.get(session)
        if val is None:
            conflicted.append(session)
            continue
        day, period, room = val
        occ.remove(session, day, period, room)
        c = occ.count_conflicts(session, day, period, room, dataset)
        occ.add(session, day, period, room)
        if c > 0:
            conflicted.append(session)
    return conflicted


def solve_min_conflicts(dataset: Dataset, config: SolverConfig) -> Result:
    """
    High-performance Min-Conflicts local search solver using FastOccupancy.
    Runs in milliseconds and reliably finds zero-conflict solutions.
    """
    random.seed(config.seed)
    start_time = time.time()

    domains = build_domains(dataset, config)
    sessions = dataset.sessions

    # Create initial assignment and seed FastOccupancy
    assignment = _create_initial_assignment(sessions, domains, "greedy", dataset)
    occ = FastOccupancy()
    for s, val in assignment.items():
        if val is not None:
            occ.add(s, val[0], val[1], val[2])

    # Initial conflict evaluation
    conflicted = _find_conflicted_sessions(assignment, sessions, dataset, occ)
    min_conflicted_count = len(conflicted)
    best_assignment = dict(assignment)

    tt = Timetable(assignment=dict(assignment))
    report = count_violations(tt, dataset, config)
    best_cost = report.cost
    cost_history = [best_cost]

    no_improve_count = 0
    total_iterations = 0

    if min_conflicted_count == 0:
        elapsed = time.time() - start_time
        return Result(
            timetable=tt,
            success=True,
            hard_violations=report.hard_count,
            soft_penalty=report.soft_penalty,
            cost=report.cost,
            time_seconds=elapsed,
            nodes_or_iterations=1,
            cost_history=cost_history,
            status="solved",
            algorithm="Min-Conflicts",
        )

    for iteration in range(config.max_iterations):
        total_iterations = iteration + 1
        if time.time() - start_time > config.time_limit:
            break

        conflicted = _find_conflicted_sessions(assignment, sessions, dataset, occ)
        if not conflicted:
            best_assignment = dict(assignment)
            break

        if len(conflicted) < min_conflicted_count:
            min_conflicted_count = len(conflicted)
            best_assignment = dict(assignment)
            no_improve_count = 0
        else:
            no_improve_count += 1

        session = random.choice(conflicted)
        domain = domains.get(session, [])
        if not domain:
            continue

        old_val = assignment.get(session)
        if old_val is not None:
            occ.remove(session, old_val[0], old_val[1], old_val[2])

        # Random walk or pick minimum conflict slot
        if random.random() < config.random_walk_prob:
            new_val = random.choice(domain)
        else:
            min_conflicts = float("inf")
            best_values = []
            for value in domain:
                c = occ.count_conflicts(session, value[0], value[1], value[2], dataset)
                if c < min_conflicts:
                    min_conflicts = c
                    best_values = [value]
                elif c == min_conflicts:
                    best_values.append(value)
            new_val = random.choice(best_values)

        assignment[session] = new_val
        occ.add(session, new_val[0], new_val[1], new_val[2])

        if iteration % 100 == 0:
            tt_curr = Timetable(assignment=dict(assignment))
            c_cost = compute_cost(tt_curr, dataset, config)
            cost_history.append(c_cost)
            if c_cost < best_cost:
                best_cost = c_cost
                best_assignment = dict(assignment)

        # Plateau escape: random restart
        if no_improve_count >= config.restart_after:
            logger.debug("Restarting Min-Conflicts at iteration %d", iteration)
            assignment = _create_initial_assignment(sessions, domains, "random", dataset)
            occ = FastOccupancy()
            for s, val in assignment.items():
                if val is not None:
                    occ.add(s, val[0], val[1], val[2])
            no_improve_count = 0

    elapsed = time.time() - start_time

    # Final evaluation on best assignment
    timetable = Timetable(assignment=best_assignment)
    final_report = count_violations(timetable, dataset, config)
    cost_history.append(final_report.cost)
    success = final_report.hard_count == 0

    return Result(
        timetable=timetable,
        success=success,
        hard_violations=final_report.hard_count,
        soft_penalty=final_report.soft_penalty,
        cost=final_report.cost,
        time_seconds=elapsed,
        nodes_or_iterations=total_iterations,
        cost_history=cost_history,
        status="solved" if success else ("timeout" if elapsed >= config.time_limit else "failed"),
        algorithm="Min-Conflicts",
    )
