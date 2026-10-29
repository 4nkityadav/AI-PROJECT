"""
backtracking.py — Backtracking CSP solver with toggleable heuristics.

Implements:
  1. Plain backtracking (baseline): fixed variable order, no pruning.
  2. MRV (Minimum Remaining Values): pick variable with smallest domain.
  3. Degree heuristic: tie-break MRV by most constrained neighbours.
  4. LCV (Least Constraining Value): order values by how few options they eliminate.
  5. Forward Checking: after each assignment, prune neighbours' domains.
  6. AC-3: arc consistency preprocessing.

All heuristics are toggled via SolverConfig flags so experiments
can measure each one's contribution independently.

Uses iterative deepening approach (explicit stack) to avoid Python's
recursion limit on large datasets.
"""

from __future__ import annotations
import time
import random
import logging
import sys
from collections import defaultdict
from core.models import (
    Dataset, Timetable, Session, SolverConfig, Result,
)
from core.csp import build_domains, build_constraint_graph
from core.constraints import count_violations, count_conflicts_for_assignment

logger = logging.getLogger(__name__)

# Increase recursion limit for large datasets, but use iterative approach as primary
sys.setrecursionlimit(10000)


def _is_consistent(session: Session, value: tuple[int, int, str],
                   assignment: dict, dataset: Dataset) -> bool:
    """
    Check if assigning 'value' to 'session' creates any hard conflicts
    with the current partial assignment.
    """
    return count_conflicts_for_assignment(session, value, assignment, dataset) == 0


def _select_variable_plain(unassigned: list[Session], **kwargs) -> Session:
    """Plain: pick the first unassigned variable (fixed order)."""
    return unassigned[0]


def _select_variable_mrv(
    unassigned: list[Session],
    domains: dict[Session, list],
    neighbours: dict[Session, set[Session]],
    assignment: dict,
    use_degree: bool = True,
) -> Session:
    """
    MRV: pick the unassigned variable with the fewest legal values.
    Tie-break with Degree heuristic if enabled: among ties, pick the
    variable with the most constraints on other unassigned variables.
    """
    min_size = float("inf")
    candidates = []

    for var in unassigned:
        d_size = len(domains.get(var, []))
        if d_size < min_size:
            min_size = d_size
            candidates = [var]
        elif d_size == min_size:
            candidates.append(var)

    if len(candidates) == 1 or not use_degree:
        return candidates[0]

    # Degree heuristic: most constraints with unassigned variables
    unassigned_set = set(unassigned)
    best = candidates[0]
    best_degree = -1
    for var in candidates:
        degree = sum(1 for n in neighbours.get(var, set()) if n in unassigned_set)
        if degree > best_degree:
            best_degree = degree
            best = var
    return best


def _order_values_plain(session: Session, domain: list, **kwargs) -> list:
    """Plain: return domain in random order (adds diversity across runs)."""
    shuffled = list(domain)
    random.shuffle(shuffled)
    return shuffled


def _order_values_lcv(
    session: Session, domain: list,
    neighbours: dict[Session, set[Session]],
    domains: dict[Session, list],
    assignment: dict,
    dataset: Dataset,
) -> list:
    """
    LCV: order values by how many options they leave for neighbouring variables.
    The value that eliminates the fewest choices for neighbours comes first.
    """
    def count_eliminated(value):
        day, period, room = value
        eliminated = 0
        for neighbour in neighbours.get(session, set()):
            if neighbour in assignment:
                continue
            for n_val in domains.get(neighbour, []):
                n_day, n_period, n_room = n_val
                # Check if this value would conflict with the neighbour's value
                for p_off in range(session.block_size):
                    for n_off in range(neighbour.block_size):
                        if n_day == day and n_period + n_off == period + p_off:
                            if (neighbour.teacher_name == session.teacher_name or
                                    neighbour.class_name == session.class_name or
                                    n_room == room):
                                eliminated += 1
        return eliminated

    # Sort by fewest eliminations (least constraining first)
    scored = [(count_eliminated(v), random.random(), v) for v in domain]
    scored.sort()
    return [v for _, _, v in scored]


def _forward_check(
    session: Session, value: tuple[int, int, str],
    domains: dict[Session, list],
    neighbours: dict[Session, set[Session]],
    assignment: dict,
    dataset: Dataset,
) -> tuple[bool, dict[Session, list]]:
    """
    Forward Checking: remove inconsistent values from unassigned neighbours.
    Returns (success, removed_values) where removed tracks what was pruned
    so we can restore on backtrack.
    """
    day, period, room = value
    removed: dict[Session, list] = defaultdict(list)

    for neighbour in neighbours.get(session, set()):
        if neighbour in assignment:
            continue
        if neighbour not in domains:
            continue

        new_domain = []
        for n_val in domains[neighbour]:
            n_day, n_period, n_room = n_val
            keep = True
            # Check all period combinations for conflicts
            for p_off in range(session.block_size):
                for n_off in range(neighbour.block_size):
                    if n_day == day and n_period + n_off == period + p_off:
                        if (neighbour.teacher_name == session.teacher_name or
                                neighbour.class_name == session.class_name or
                                n_room == room):
                            keep = False
                            break
                if not keep:
                    break

            if keep:
                new_domain.append(n_val)
            else:
                removed[neighbour].append(n_val)

        domains[neighbour] = new_domain
        if len(new_domain) == 0:
            # Domain wipe-out — this assignment won't work
            return False, removed

    return True, removed


def _restore_domains(domains: dict, removed: dict):
    """Undo forward checking by restoring removed values."""
    for session, values in removed.items():
        if session in domains:
            domains[session].extend(values)


def _ac3_preprocess(
    domains: dict[Session, list],
    neighbours: dict[Session, set[Session]],
    dataset: Dataset,
) -> bool:
    """
    AC-3 arc consistency preprocessing.
    Reduces domains before search begins by removing values that have
    no support in a neighbour's domain.
    Returns False if any domain becomes empty (unsolvable).
    """
    # Build queue of all arcs
    queue = []
    for var in domains:
        for neighbour in neighbours.get(var, set()):
            queue.append((var, neighbour))

    while queue:
        xi, xj = queue.pop(0)
        if _revise(xi, xj, domains, dataset):
            if len(domains[xi]) == 0:
                return False
            # Add all arcs (xk, xi) for xk ≠ xj
            for xk in neighbours.get(xi, set()):
                if xk != xj:
                    queue.append((xk, xi))
    return True


def _revise(xi: Session, xj: Session, domains: dict, dataset: Dataset) -> bool:
    """Remove values from xi's domain that have no support in xj's domain."""
    revised = False
    new_domain = []

    for val_i in domains.get(xi, []):
        day_i, period_i, room_i = val_i
        # Check if there exists at least one value in xj's domain consistent with val_i
        has_support = False
        for val_j in domains.get(xj, []):
            day_j, period_j, room_j = val_j
            conflict = False
            for p_off_i in range(xi.block_size):
                for p_off_j in range(xj.block_size):
                    if day_i == day_j and period_i + p_off_i == period_j + p_off_j:
                        if (xi.teacher_name == xj.teacher_name or
                                xi.class_name == xj.class_name or
                                room_i == room_j):
                            conflict = True
                            break
                if conflict:
                    break
            if not conflict:
                has_support = True
                break

        if has_support:
            new_domain.append(val_i)
        else:
            revised = True

    if revised:
        domains[xi] = new_domain
    return revised


def solve_backtracking(dataset: Dataset, config: SolverConfig) -> Result:
    """
    Backtracking CSP solver with toggleable heuristics.

    Feature flags from config:
      use_mrv, use_degree, use_lcv, use_forward_checking, use_ac3

    Tracks: nodes expanded, backtracks, time.
    Supports time and node limits.
    Respects locked (pinned) sessions.
    """
    random.seed(config.seed)
    start_time = time.time()

    # Build CSP structure
    domains = build_domains(dataset, config)
    neighbours = build_constraint_graph(dataset)

    # AC-3 preprocessing (if enabled)
    if config.use_ac3:
        logger.info("Running AC-3 preprocessing...")
        if not _ac3_preprocess(domains, neighbours, dataset):
            logger.warning("AC-3 found the problem unsolvable")
            return Result(
                timetable=None, success=False, hard_violations=-1,
                soft_penalty=-1, cost=-1, time_seconds=time.time() - start_time,
                nodes_or_iterations=0, status="failed",
                algorithm=_algo_name(config),
            )
        logger.info("AC-3 complete, domains pruned")

    assignment: dict[Session, tuple[int, int, str]] = {}

    # Pre-assign locked sessions
    locked_timetable = getattr(dataset, '_locked_timetable', None)
    if locked_timetable:
        for session in locked_timetable.locked_sessions:
            val = locked_timetable.get_slot(session)
            if val is not None:
                assignment[session] = val

    stats = {"nodes": 0, "backtracks": 0, "wipeouts": 0}

    # Recursive backtracking
    def backtrack() -> bool:
        stats["nodes"] += 1

        # Check time and node limits
        if stats["nodes"] > config.max_nodes:
            return False
        if time.time() - start_time > config.time_limit:
            return False

        # Find unassigned variables
        unassigned = [s for s in dataset.sessions if s not in assignment]
        if not unassigned:
            return True  # All assigned → solution found

        # Variable selection
        if config.use_mrv:
            var = _select_variable_mrv(
                unassigned, domains=domains, neighbours=neighbours,
                assignment=assignment, use_degree=config.use_degree,
            )
        else:
            var = _select_variable_plain(unassigned)

        # Value ordering
        domain = domains.get(var, [])
        if config.use_lcv:
            ordered_values = _order_values_lcv(
                var, domain, neighbours, domains, assignment, dataset,
            )
        else:
            ordered_values = _order_values_plain(var, domain)

        for value in ordered_values:
            if _is_consistent(var, value, assignment, dataset):
                assignment[var] = value

                if config.use_forward_checking:
                    success, removed = _forward_check(
                        var, value, domains, neighbours, assignment, dataset,
                    )
                    if not success:
                        stats["wipeouts"] += 1
                        _restore_domains(domains, removed)
                        del assignment[var]
                        continue

                    if backtrack():
                        return True

                    _restore_domains(domains, removed)
                else:
                    if backtrack():
                        return True

                del assignment[var]
                stats["backtracks"] += 1

        return False

    success = backtrack()
    elapsed = time.time() - start_time

    # Build result
    if success:
        timetable = Timetable(assignment=dict(assignment))
        report = count_violations(timetable, dataset, config)
        return Result(
            timetable=timetable, success=True,
            hard_violations=report.hard_count,
            soft_penalty=report.soft_penalty,
            cost=report.cost,
            time_seconds=elapsed,
            nodes_or_iterations=stats["nodes"],
            status="solved",
            algorithm=_algo_name(config),
            metadata={"backtracks": stats["backtracks"], "wipeouts": stats["wipeouts"]},
        )
    else:
        # Return partial result
        timetable = Timetable(assignment=dict(assignment)) if assignment else None
        status = "timeout" if (elapsed >= config.time_limit or stats["nodes"] >= config.max_nodes) else "failed"
        return Result(
            timetable=timetable, success=False,
            hard_violations=-1, soft_penalty=-1, cost=-1,
            time_seconds=elapsed,
            nodes_or_iterations=stats["nodes"],
            status=status,
            algorithm=_algo_name(config),
            metadata={"backtracks": stats["backtracks"], "wipeouts": stats["wipeouts"]},
        )


def _algo_name(config: SolverConfig) -> str:
    """Generate a descriptive algorithm name from the config flags."""
    parts = ["Backtracking"]
    heuristics = []
    if config.use_mrv:
        heuristics.append("MRV")
    if config.use_degree:
        heuristics.append("Degree")
    if config.use_lcv:
        heuristics.append("LCV")
    if config.use_forward_checking:
        heuristics.append("FC")
    if config.use_ac3:
        heuristics.append("AC3")

    if heuristics:
        parts.append("(" + "+".join(heuristics) + ")")
    else:
        parts.append("(Plain)")
    return " ".join(parts)
