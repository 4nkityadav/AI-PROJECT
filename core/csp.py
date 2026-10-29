"""
csp.py — CSP formulation: variables, domains, constraint graph.

This module builds the CSP structure that the backtracking solver uses:
  - Variables = list of Session objects (created by teacher_assign.py)
  - Domain(session) = list of (day, period, room) triples after unary pruning
  - Neighbours(session) = set of sessions that share a constraint

Unary pruning removes values that violate:
  H5 (room type), H4 (capacity), H6 (teacher availability),
  H9 (lunch break), break periods, and period overflow for blocks.
"""

from __future__ import annotations
import logging
from collections import defaultdict
from core.models import Dataset, Session, SolverConfig

logger = logging.getLogger(__name__)


def build_domains(
    dataset: Dataset,
    config: SolverConfig | None = None,
) -> dict[Session, list[tuple[int, int, str]]]:
    """
    Build the domain for each session variable after unary constraint pruning.

    A domain value is a (day, period, room_name) triple.
    For block sessions (block_size > 1), 'period' is the start period,
    and the session occupies [period, period + block_size - 1].
    """
    if config is None:
        config = SolverConfig()

    ts = dataset.time_structure
    domains: dict[Session, list[tuple[int, int, str]]] = {}

    for session in dataset.sessions:
        domain = []
        subj = dataset.subjects.get(session.subject_code)
        if subj is None:
            continue

        # Determine which room type is needed
        needed_room_type = "lab" if subj.subject_type == "lab" else "classroom"
        cls = dataset.classes.get(session.class_name)
        if cls is None:
            continue

        # Get teacher's unavailable slots as a set for O(1) lookup
        teacher = dataset.teachers.get(session.teacher_name)
        unavail_set = set(teacher.unavailable_slots) if teacher else set()

        for day in range(ts.working_days):
            for period in range(ts.periods_per_day):
                # Check if block fits within the day
                if period + session.block_size > ts.periods_per_day:
                    continue

                # Check all periods the block would occupy
                valid = True
                for p_off in range(session.block_size):
                    p = period + p_off
                    # Skip break periods
                    if p in ts.break_periods:
                        valid = False
                        break
                    # H9: skip lunch period for this class
                    if p == cls.lunch_break_slot:
                        valid = False
                        break
                    # H6: teacher must be available
                    if (day, p) in unavail_set:
                        valid = False
                        break

                if not valid:
                    continue

                # Try each room of the correct type with sufficient capacity
                for room_name, room in dataset.rooms.items():
                    # H5: room type must match
                    if room.room_type != needed_room_type:
                        continue
                    # H4: room must fit the class
                    if room.capacity < cls.strength:
                        continue

                    domain.append((day, period, room_name))

        domains[session] = domain
        if len(domain) == 0:
            logger.warning("Session %s has EMPTY domain — problem may be unsolvable", session.label())

    logger.info("Built domains for %d sessions (avg size: %.1f)",
                len(domains),
                sum(len(d) for d in domains.values()) / max(len(domains), 1))
    return domains


def build_constraint_graph(
    dataset: Dataset,
) -> dict[Session, set[Session]]:
    """
    Build the constraint graph: neighbours[session] = set of sessions
    that share at least one binary constraint with it.

    Two sessions are neighbours if they share:
      - The same teacher (H1)
      - The same class (H2)
      - Could use the same room (H3) — we simplify: same room type needed

    This graph is used by the Degree heuristic and Forward Checking.
    """
    neighbours: dict[Session, set[Session]] = defaultdict(set)

    sessions = dataset.sessions
    n = len(sessions)

    for i in range(n):
        for j in range(i + 1, n):
            a, b = sessions[i], sessions[j]
            connected = False

            # Same teacher → H1 constraint
            if a.teacher_name == b.teacher_name:
                connected = True

            # Same class → H2 constraint
            if a.class_name == b.class_name:
                connected = True

            # Could share a room → H3 constraint
            # (only if they need the same room type)
            if not connected:
                subj_a = dataset.subjects.get(a.subject_code)
                subj_b = dataset.subjects.get(b.subject_code)
                if subj_a and subj_b:
                    type_a = "lab" if subj_a.subject_type == "lab" else "classroom"
                    type_b = "lab" if subj_b.subject_type == "lab" else "classroom"
                    if type_a == type_b:
                        connected = True

            if connected:
                neighbours[a].add(b)
                neighbours[b].add(a)

    logger.info("Constraint graph: %d edges",
                sum(len(v) for v in neighbours.values()) // 2)
    return neighbours
