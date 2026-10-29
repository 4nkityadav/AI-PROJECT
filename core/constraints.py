"""
constraints.py — Single source of truth for all constraint checking.

The function count_violations() is used by:
  - Both solvers (backtracking, min-conflicts, SA, etc.)
  - The manual-edit feature (to flag conflicts)
  - The experiments module (to evaluate solutions)

Design:
  - Each hard constraint (H1-H9) and soft constraint (S1-S5) has its own
    function that returns a list of ViolationDetail objects.
  - count_violations() aggregates them into a ViolationReport.
  - The cost function is: Cost = 1000 * hard_count + weighted soft penalty.
  - Weights are configurable via SolverConfig.
"""

from __future__ import annotations
import logging
from collections import defaultdict
from core.models import (
    Dataset, Timetable, Session, SolverConfig,
    ViolationDetail, ViolationReport,
)

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════
# Occupancy tables — built once, used by all checks
# ════════════════════════════════════════════

def _build_occupancy(timetable: Timetable, dataset: Dataset):
    """
    Build lookup tables for who/what is in each (day, period) slot.
    Returns dicts keyed by (day, period) containing lists.
    This avoids O(n^2) pairwise comparisons.
    """
    teacher_at = defaultdict(list)   # (day, period) -> [session, ...]
    class_at = defaultdict(list)     # (day, period) -> [session, ...]
    room_at = defaultdict(list)      # (day, period, room) -> [session, ...]

    for session, value in timetable.assignment.items():
        if value is None:
            continue
        day, period, room = value
        # For block sessions (labs), occupy multiple consecutive periods
        for p_offset in range(session.block_size):
            slot = (day, period + p_offset)
            teacher_at[slot].append(session)
            class_at[slot].append(session)
            room_at[(day, period + p_offset, room)].append(session)

    return teacher_at, class_at, room_at


# ════════════════════════════════════════════
# Hard constraint checkers (H1 — H9)
# ════════════════════════════════════════════

def _check_h1_teacher_clash(teacher_at: dict, dataset: Dataset) -> list[ViolationDetail]:
    """H1: A teacher cannot teach two sessions at the same time."""
    violations = []
    for (day, period), sessions in teacher_at.items():
        by_teacher = defaultdict(list)
        for s in sessions:
            by_teacher[s.teacher_name].append(s)
        for t_name, sess_list in by_teacher.items():
            if len(sess_list) > 1:
                violations.append(ViolationDetail(
                    code="H1",
                    message=f"Teacher {t_name} has {len(sess_list)} sessions at day {day+1} period {period+1}",
                    sessions=sess_list, day=day, period=period,
                ))
    return violations


def _check_h2_class_clash(class_at: dict, dataset: Dataset) -> list[ViolationDetail]:
    """H2: A class cannot have two sessions at the same time."""
    violations = []
    for (day, period), sessions in class_at.items():
        by_class = defaultdict(list)
        for s in sessions:
            by_class[s.class_name].append(s)
        for cls_name, sess_list in by_class.items():
            if len(sess_list) > 1:
                violations.append(ViolationDetail(
                    code="H2",
                    message=f"Class {cls_name} has {len(sess_list)} sessions at day {day+1} period {period+1}",
                    sessions=sess_list, day=day, period=period,
                ))
    return violations


def _check_h3_room_clash(room_at: dict, dataset: Dataset) -> list[ViolationDetail]:
    """H3: A room cannot be used for two sessions at the same time."""
    violations = []
    for (day, period, room), sessions in room_at.items():
        if len(sessions) > 1:
            violations.append(ViolationDetail(
                code="H3",
                message=f"Room {room} has {len(sessions)} sessions at day {day+1} period {period+1}",
                sessions=sessions, day=day, period=period,
            ))
    return violations


def _check_h4_room_capacity(timetable: Timetable, dataset: Dataset) -> list[ViolationDetail]:
    """H4: Room capacity must be at least the class strength."""
    violations = []
    for session, value in timetable.assignment.items():
        if value is None:
            continue
        day, period, room_name = value
        if room_name in dataset.rooms and session.class_name in dataset.classes:
            room = dataset.rooms[room_name]
            cls = dataset.classes[session.class_name]
            if room.capacity < cls.strength:
                violations.append(ViolationDetail(
                    code="H4",
                    message=(f"Room {room_name} (cap={room.capacity}) too small for "
                             f"class {session.class_name} (strength={cls.strength})"),
                    sessions=[session], day=day, period=period,
                ))
    return violations


def _check_h5_room_type(timetable: Timetable, dataset: Dataset) -> list[ViolationDetail]:
    """H5: Lab sessions in lab rooms; theory sessions in classrooms."""
    violations = []
    for session, value in timetable.assignment.items():
        if value is None:
            continue
        day, period, room_name = value
        if session.subject_code in dataset.subjects and room_name in dataset.rooms:
            subj = dataset.subjects[session.subject_code]
            room = dataset.rooms[room_name]
            expected = "lab" if subj.subject_type == "lab" else "classroom"
            if room.room_type != expected:
                violations.append(ViolationDetail(
                    code="H5",
                    message=(f"{subj.subject_type.title()} subject {session.subject_code} "
                             f"assigned to {room.room_type} {room_name}"),
                    sessions=[session], day=day, period=period,
                ))
    return violations


def _check_h6_teacher_availability(timetable: Timetable, dataset: Dataset) -> list[ViolationDetail]:
    """H6: Teacher can only be scheduled in available slots."""
    violations = []
    for session, value in timetable.assignment.items():
        if value is None:
            continue
        day, period, _ = value
        if session.teacher_name in dataset.teachers:
            teacher = dataset.teachers[session.teacher_name]
            for p_offset in range(session.block_size):
                if (day, period + p_offset) in teacher.unavailable_slots:
                    violations.append(ViolationDetail(
                        code="H6",
                        message=(f"Teacher {session.teacher_name} unavailable at "
                                 f"day {day+1} period {period+p_offset+1}"),
                        sessions=[session], day=day, period=period + p_offset,
                    ))
    return violations


def _check_h7_weekly_hours(timetable: Timetable, dataset: Dataset) -> list[ViolationDetail]:
    """H7: Every subject gets exactly its required weekly hours."""
    violations = []
    # Count assigned hours per (class, subject)
    assigned = defaultdict(int)
    for session, value in timetable.assignment.items():
        if value is not None:
            assigned[(session.class_name, session.subject_code)] += session.block_size

    # Check against required
    for cls_name, cls in dataset.classes.items():
        for sc in cls.subjects:
            if sc in dataset.subjects:
                required = dataset.subjects[sc].weekly_hours
                got = assigned.get((cls_name, sc), 0)
                if got != required:
                    violations.append(ViolationDetail(
                        code="H7",
                        message=f"{cls_name}/{sc}: assigned {got} hours, required {required}",
                        sessions=[],
                    ))
    return violations


def _check_h8_teacher_load(timetable: Timetable, dataset: Dataset) -> list[ViolationDetail]:
    """H8: Teacher's weekly load must not exceed max_weekly_load."""
    violations = []
    load = defaultdict(int)
    for session, value in timetable.assignment.items():
        if value is not None:
            load[session.teacher_name] += session.block_size

    for t_name, hours in load.items():
        if t_name in dataset.teachers:
            max_load = dataset.teachers[t_name].max_weekly_load
            if hours > max_load:
                violations.append(ViolationDetail(
                    code="H8",
                    message=f"Teacher {t_name}: load {hours} exceeds max {max_load}",
                    sessions=[],
                ))
    return violations


def _check_h9_lunch_break(timetable: Timetable, dataset: Dataset) -> list[ViolationDetail]:
    """H9: No session during a class's lunch break slot."""
    violations = []
    for session, value in timetable.assignment.items():
        if value is None:
            continue
        day, period, _ = value
        if session.class_name in dataset.classes:
            lunch = dataset.classes[session.class_name].lunch_break_slot
            # Check if any period of a block session overlaps lunch
            for p_offset in range(session.block_size):
                if period + p_offset == lunch:
                    violations.append(ViolationDetail(
                        code="H9",
                        message=(f"Class {session.class_name} has session during lunch "
                                 f"(period {lunch+1}) on day {day+1}"),
                        sessions=[session], day=day, period=lunch,
                    ))
    return violations


# ════════════════════════════════════════════
# Soft constraint checkers (S1 — S5)
# ════════════════════════════════════════════

def _check_s1_gaps(timetable: Timetable, dataset: Dataset) -> list[ViolationDetail]:
    """S1: Minimise free periods (gaps) in a class's day."""
    violations = []
    ts = dataset.time_structure

    # Build class day schedule
    class_day_periods: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for session, value in timetable.assignment.items():
        if value is None:
            continue
        day, period, _ = value
        for p_off in range(session.block_size):
            class_day_periods[session.class_name][day].append(period + p_off)

    for cls_name, day_map in class_day_periods.items():
        lunch = dataset.classes[cls_name].lunch_break_slot if cls_name in dataset.classes else -1
        for day, periods in day_map.items():
            if len(periods) < 2:
                continue
            sorted_p = sorted(set(periods))
            for i in range(len(sorted_p) - 1):
                for gap_p in range(sorted_p[i] + 1, sorted_p[i + 1]):
                    if gap_p != lunch and gap_p not in ts.break_periods:
                        violations.append(ViolationDetail(
                            code="S1",
                            message=f"Class {cls_name} has a gap at day {day+1} period {gap_p+1}",
                            sessions=[], day=day, period=gap_p,
                        ))
    return violations


def _check_s2_subject_spread(timetable: Timetable, dataset: Dataset) -> list[ViolationDetail]:
    """S2: Avoid same subject twice in one day (except labs)."""
    violations = []
    # Count per (class, subject, day)
    counts: dict[tuple, int] = defaultdict(int)
    for session, value in timetable.assignment.items():
        if value is None:
            continue
        day, _, _ = value
        # Labs are exempt from this constraint
        if session.subject_code in dataset.subjects:
            if dataset.subjects[session.subject_code].subject_type == "lab":
                continue
        counts[(session.class_name, session.subject_code, day)] += 1

    for (cls, subj, day), count in counts.items():
        if count > 1:
            violations.append(ViolationDetail(
                code="S2",
                message=f"{cls}: subject {subj} appears {count} times on day {day+1}",
                sessions=[], day=day, period=-1,
            ))
    return violations


def _check_s3_lab_consecutive(timetable: Timetable, dataset: Dataset) -> list[ViolationDetail]:
    """S3: Lab sessions should occupy consecutive periods (for split mode)."""
    violations = []
    # Group lab sessions by (class, subject, day)
    lab_slots: dict[tuple, list[int]] = defaultdict(list)
    for session, value in timetable.assignment.items():
        if value is None:
            continue
        if session.subject_code in dataset.subjects:
            if dataset.subjects[session.subject_code].subject_type == "lab":
                day, period, _ = value
                lab_slots[(session.class_name, session.subject_code, day)].append(period)

    for key, periods in lab_slots.items():
        if len(periods) < 2:
            continue
        sorted_p = sorted(periods)
        for i in range(len(sorted_p) - 1):
            if sorted_p[i + 1] - sorted_p[i] != 1:
                cls, subj, day = key
                violations.append(ViolationDetail(
                    code="S3",
                    message=f"Lab {subj} for {cls} not consecutive on day {day+1}",
                    sessions=[], day=day, period=sorted_p[i],
                ))
    return violations


def _check_s4_teacher_preferences(timetable: Timetable, dataset: Dataset) -> list[ViolationDetail]:
    """S4: Respect teacher period preferences (avoid_periods)."""
    violations = []
    for session, value in timetable.assignment.items():
        if value is None:
            continue
        day, period, _ = value
        if session.teacher_name in dataset.teachers:
            teacher = dataset.teachers[session.teacher_name]
            for p_off in range(session.block_size):
                if (period + p_off) in teacher.avoid_periods:
                    violations.append(ViolationDetail(
                        code="S4",
                        message=(f"Teacher {session.teacher_name} prefers to avoid "
                                 f"period {period+p_off+1} (day {day+1})"),
                        sessions=[session], day=day, period=period + p_off,
                    ))
    return violations


def _check_s5_teacher_consecutive(timetable: Timetable, dataset: Dataset) -> list[ViolationDetail]:
    """S5: Avoid more than 2 consecutive lectures for a teacher."""
    violations = []
    ts = dataset.time_structure

    # Build teacher-day schedule
    teacher_day_periods: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for session, value in timetable.assignment.items():
        if value is None:
            continue
        day, period, _ = value
        for p_off in range(session.block_size):
            teacher_day_periods[session.teacher_name][day].append(period + p_off)

    for t_name, day_map in teacher_day_periods.items():
        for day, periods in day_map.items():
            sorted_p = sorted(set(periods))
            # Check for runs of 3+ consecutive periods
            run_length = 1
            for i in range(1, len(sorted_p)):
                if sorted_p[i] == sorted_p[i - 1] + 1:
                    run_length += 1
                    if run_length > 2:
                        violations.append(ViolationDetail(
                            code="S5",
                            message=(f"Teacher {t_name} has {run_length} consecutive "
                                     f"lectures on day {day+1} (periods {sorted_p[i-run_length+1]+1}-{sorted_p[i]+1})"),
                            sessions=[], day=day, period=sorted_p[i],
                        ))
                else:
                    run_length = 1
    return violations


# ════════════════════════════════════════════
# Main entry point
# ════════════════════════════════════════════

def count_violations(timetable: Timetable, dataset: Dataset,
                     config: SolverConfig | None = None) -> ViolationReport:
    """
    Count ALL hard and soft violations in a timetable.

    This is the SINGLE SOURCE OF TRUTH for constraint checking.
    Used by solvers, manual editor, and experiments.

    Returns a ViolationReport with per-constraint breakdown.
    """
    if config is None:
        config = SolverConfig()

    report = ViolationReport()

    # Build occupancy tables once
    teacher_at, class_at, room_at = _build_occupancy(timetable, dataset)

    # Hard constraints
    hard_checks = [
        _check_h1_teacher_clash(teacher_at, dataset),
        _check_h2_class_clash(class_at, dataset),
        _check_h3_room_clash(room_at, dataset),
        _check_h4_room_capacity(timetable, dataset),
        _check_h5_room_type(timetable, dataset),
        _check_h6_teacher_availability(timetable, dataset),
        _check_h7_weekly_hours(timetable, dataset),
        _check_h8_teacher_load(timetable, dataset),
        _check_h9_lunch_break(timetable, dataset),
    ]
    for check_result in hard_checks:
        report.hard_violations.extend(check_result)

    report.hard_count = len(report.hard_violations)

    # Soft constraints
    soft_checks = [
        (_check_s1_gaps(timetable, dataset), config.weight_s1),
        (_check_s2_subject_spread(timetable, dataset), config.weight_s2),
        (_check_s3_lab_consecutive(timetable, dataset), config.weight_s3),
        (_check_s4_teacher_preferences(timetable, dataset), config.weight_s4),
        (_check_s5_teacher_consecutive(timetable, dataset), config.weight_s5),
    ]
    for check_result, weight in soft_checks:
        report.soft_violations.extend(check_result)
        report.soft_penalty += len(check_result) * weight

    # Cost function: 1000 * hard + soft
    report.cost = 1000 * report.hard_count + report.soft_penalty

    # Per-code breakdown — initialise ALL codes so they always appear
    report.per_code = {
        "H1": 0, "H2": 0, "H3": 0, "H4": 0, "H5": 0,
        "H6": 0, "H7": 0, "H8": 0, "H9": 0,
        "S1": 0, "S2": 0, "S3": 0, "S4": 0, "S5": 0,
    }
    for v in report.hard_violations + report.soft_violations:
        report.per_code[v.code] = report.per_code.get(v.code, 0) + 1

    return report


def compute_cost(timetable: Timetable, dataset: Dataset,
                 config: SolverConfig | None = None) -> float:
    """Convenience function that returns just the cost number."""
    return count_violations(timetable, dataset, config).cost


# ════════════════════════════════════════════
# Fast incremental check for a single session assignment
# Used by solvers for speed (avoids recounting everything)
# ════════════════════════════════════════════

def count_conflicts_for_assignment(
    session: Session, value: tuple[int, int, str],
    current_assignment: dict, dataset: Dataset,
) -> int:
    """
    Count hard conflicts that would result from assigning 'value' to 'session'.
    Checks only against existing assignments in current_assignment.
    Much faster than a full count_violations() call.
    Used by backtracking is_consistent() and min-conflicts value selection.
    """
    day, period, room_name = value
    conflicts = 0

    # H9: Lunch break
    if session.class_name in dataset.classes:
        lunch = dataset.classes[session.class_name].lunch_break_slot
        for p_off in range(session.block_size):
            if period + p_off == lunch:
                conflicts += 1

    # H6: Teacher availability
    if session.teacher_name in dataset.teachers:
        teacher = dataset.teachers[session.teacher_name]
        for p_off in range(session.block_size):
            if (day, period + p_off) in teacher.unavailable_slots:
                conflicts += 1

    # H4: Room capacity
    if room_name in dataset.rooms and session.class_name in dataset.classes:
        if dataset.rooms[room_name].capacity < dataset.classes[session.class_name].strength:
            conflicts += 1

    # H5: Room type
    if session.subject_code in dataset.subjects and room_name in dataset.rooms:
        subj = dataset.subjects[session.subject_code]
        room = dataset.rooms[room_name]
        expected = "lab" if subj.subject_type == "lab" else "classroom"
        if room.room_type != expected:
            conflicts += 1

    # Check period overflow for block sessions
    if period + session.block_size > dataset.time_structure.periods_per_day:
        conflicts += 1

    # Binary constraints: check against other assigned sessions
    for other, other_val in current_assignment.items():
        if other is session or other_val is None:
            continue
        o_day, o_period, o_room = other_val

        # Check all periods this session would occupy
        for p_off in range(session.block_size):
            cur_period = period + p_off
            # And all periods the other session occupies
            for o_off in range(other.block_size):
                if o_day == day and o_period + o_off == cur_period:
                    # H1: teacher clash
                    if other.teacher_name == session.teacher_name:
                        conflicts += 1
                    # H2: class clash
                    if other.class_name == session.class_name:
                        conflicts += 1
                    # H3: room clash
                    if o_room == room_name:
                        conflicts += 1

    return conflicts


class FastOccupancy:
    """
    High-performance incremental slot occupancy tracker.
    Provides O(1) clash detection for teacher, class, and room conflicts.
    Replaces quadratic loop iterations in local search, hybrid, and backtracking.
    """

    def __init__(self):
        from collections import Counter
        self.teacher_at: dict[tuple[int, int], Counter[str]] = defaultdict(Counter)
        self.class_at: dict[tuple[int, int], Counter[str]] = defaultdict(Counter)
        self.room_at: dict[tuple[int, int], Counter[str]] = defaultdict(Counter)

    def add(self, session: Session, day: int, period: int, room: str):
        for p_off in range(session.block_size):
            slot = (day, period + p_off)
            self.teacher_at[slot][session.teacher_name] += 1
            self.class_at[slot][session.class_name] += 1
            self.room_at[slot][room] += 1

    def remove(self, session: Session, day: int, period: int, room: str):
        for p_off in range(session.block_size):
            slot = (day, period + p_off)
            t_cnt = self.teacher_at[slot]
            t_cnt[session.teacher_name] -= 1
            if t_cnt[session.teacher_name] <= 0:
                del t_cnt[session.teacher_name]

            c_cnt = self.class_at[slot]
            c_cnt[session.class_name] -= 1
            if c_cnt[session.class_name] <= 0:
                del c_cnt[session.class_name]

            r_cnt = self.room_at[slot]
            r_cnt[room] -= 1
            if r_cnt[room] <= 0:
                del r_cnt[room]

    def count_conflicts(self, session: Session, day: int, period: int, room: str, dataset: Dataset) -> int:
        conflicts = 0
        cls = dataset.classes.get(session.class_name)
        teacher = dataset.teachers.get(session.teacher_name)

        # Period overflow check
        if period + session.block_size > dataset.time_structure.periods_per_day:
            conflicts += 1

        for p_off in range(session.block_size):
            p = period + p_off
            slot = (day, p)
            # H1: Teacher clash
            if session.teacher_name in self.teacher_at[slot]:
                conflicts += 1
            # H2: Class clash
            if session.class_name in self.class_at[slot]:
                conflicts += 1
            # H3: Room clash
            if room in self.room_at[slot]:
                conflicts += 1
            # H6: Teacher availability
            if teacher and (day, p) in teacher.unavailable_slots:
                conflicts += 1
            # H9: Lunch break
            if cls and p == cls.lunch_break_slot:
                conflicts += 1

        # H4: Room capacity
        if room in dataset.rooms and session.class_name in dataset.classes:
            if dataset.rooms[room].capacity < dataset.classes[session.class_name].strength:
                conflicts += 1

        # H5: Room type
        subj = dataset.subjects.get(session.subject_code)
        if subj and room in dataset.rooms:
            expected = "lab" if subj.subject_type == "lab" else "classroom"
            if dataset.rooms[room].room_type != expected:
                conflicts += 1

        return conflicts
