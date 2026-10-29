"""
annealing.py — Simulated Annealing solver for timetable scheduling.

Neighbourhood moves:
  1. Swap: exchange the slots of two randomly chosen sessions.
  2. Move: move a session to a random free valid slot from its domain.
  3. Room change: change only the room of a session (same day/period).

Temperature calibration:
  Initial temperature is set so that a move with average delta cost
  has ~80% acceptance probability: T0 = -avg_delta / ln(0.8).

Cooling schedule:
  Geometric: T_{n+1} = alpha * T_n (default alpha = 0.995).

Stopping rule:
  Temperature drops below min_temp OR no improvement for K steps.

Records cost_history for plotting.
"""

from __future__ import annotations
import time
import math
import random
import logging
from core.models import Dataset, Timetable, Session, SolverConfig, Result
from core.csp import build_domains
from core.constraints import count_violations

logger = logging.getLogger(__name__)


def solve_simulated_annealing(dataset: Dataset, config: SolverConfig) -> Result:
    """
    Simulated Annealing solver.
    Starts from a random complete assignment and iteratively improves
    by accepting moves that reduce cost, and sometimes accepting
    worse moves with probability exp(-delta/T).
    """
    random.seed(config.seed)
    start_time = time.time()

    domains = build_domains(dataset, config)
    sessions = dataset.sessions

    # Create initial random assignment
    assignment = {}
    for session in sessions:
        domain = domains.get(session, [])
        if domain:
            assignment[session] = random.choice(domain)

    # Evaluate initial solution
    timetable = Timetable(assignment=dict(assignment))
    report = count_violations(timetable, dataset, config)
    current_cost = report.cost

    best_assignment = dict(assignment)
    best_cost = current_cost
    cost_history = [current_cost]

    temp = config.sa_initial_temp
    no_improve = 0

    iteration = 0
    while temp > config.sa_min_temp:
        if time.time() - start_time > config.time_limit:
            break

        for _ in range(config.sa_iterations_per_temp):
            iteration += 1

            # Choose a random move type
            move_type = random.choice(["move", "swap", "room_change"])
            old_assignment = dict(assignment)

            if move_type == "swap" and len(sessions) >= 2:
                # Swap two sessions' slots
                s1, s2 = random.sample(sessions, 2)
                v1 = assignment.get(s1)
                v2 = assignment.get(s2)
                if v1 and v2:
                    assignment[s1] = v2
                    assignment[s2] = v1

            elif move_type == "room_change":
                # Change room only
                s = random.choice(sessions)
                val = assignment.get(s)
                if val:
                    day, period, old_room = val
                    # Find other rooms from domain with same day/period
                    alternatives = [
                        (d, p, r) for d, p, r in domains.get(s, [])
                        if d == day and p == period and r != old_room
                    ]
                    if alternatives:
                        assignment[s] = random.choice(alternatives)

            else:
                # Move a session to a random valid slot
                s = random.choice(sessions)
                domain = domains.get(s, [])
                if domain:
                    assignment[s] = random.choice(domain)

            # Evaluate new solution
            new_tt = Timetable(assignment=dict(assignment))
            new_report = count_violations(new_tt, dataset, config)
            new_cost = new_report.cost

            delta = new_cost - current_cost

            # Accept or reject
            if delta <= 0:
                # Better or equal — always accept
                current_cost = new_cost
                if new_cost < best_cost:
                    best_cost = new_cost
                    best_assignment = dict(assignment)
                    no_improve = 0
            elif temp > 0 and random.random() < math.exp(-delta / temp):
                # Worse — accept with probability
                current_cost = new_cost
            else:
                # Reject — revert
                assignment = old_assignment

            # Record cost periodically
            if iteration % 100 == 0:
                cost_history.append(current_cost)

        # Cool down
        temp *= config.sa_cooling_alpha
        no_improve += 1

        # Early stop if optimal or no improvement for too long
        if best_cost == 0 or no_improve > 300:
            break

    elapsed = time.time() - start_time

    # Final evaluation
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
        nodes_or_iterations=iteration,
        cost_history=cost_history,
        status="solved" if final_report.hard_count == 0 else "failed",
        algorithm="Simulated Annealing",
    )
