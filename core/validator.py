"""
validator.py — Validate a Dataset for completeness and solvability.

Two levels of checking:
1. Structural validation: required fields, no duplicates, references exist.
2. Solvability pre-check: enough room-slots, teacher hours, class hours.

Returns lists of errors (fatal) and warnings (informational).
"""

from __future__ import annotations
import logging
from core.models import Dataset

logger = logging.getLogger(__name__)


def validate_dataset(dataset: Dataset) -> tuple[list[str], list[str]]:
    """
    Validate the dataset.
    Returns (errors, warnings).  errors = [] means dataset is valid.
    """
    errors: list[str] = []
    warnings: list[str] = []
    ts = dataset.time_structure

    # ── Structural checks ──

    # Duplicate codes/names
    seen_codes = set()
    for code in dataset.subjects:
        if code in seen_codes:
            errors.append(f"Duplicate subject code: {code}")
        seen_codes.add(code)

    seen_names = set()
    for name in dataset.teachers:
        if name in seen_names:
            errors.append(f"Duplicate teacher name: {name}")
        seen_names.add(name)

    seen_names = set()
    for name in dataset.classes:
        if name in seen_names:
            errors.append(f"Duplicate class name: {name}")
        seen_names.add(name)

    seen_names = set()
    for name in dataset.rooms:
        if name in seen_names:
            errors.append(f"Duplicate room name: {name}")
        seen_names.add(name)

    # Every class subject must exist
    for cls_name, cls in dataset.classes.items():
        for sc in cls.subjects:
            if sc not in dataset.subjects:
                errors.append(f"Class '{cls_name}' references unknown subject '{sc}'")

    # Every subject must have at least one teacher
    dataset.build_subject_teachers()
    all_needed_subjects = set()
    for cls in dataset.classes.values():
        all_needed_subjects.update(cls.subjects)
    for sc in all_needed_subjects:
        if sc not in dataset.subject_teachers or len(dataset.subject_teachers[sc]) == 0:
            errors.append(f"Subject '{sc}' has no eligible teacher")

    # Teacher subjects must exist
    for t_name, teacher in dataset.teachers.items():
        for sc in teacher.subjects:
            if sc not in dataset.subjects:
                warnings.append(f"Teacher '{t_name}' lists unknown subject '{sc}'")

    # Lunch slot and break periods must be valid
    for cls_name, cls in dataset.classes.items():
        if cls.lunch_break_slot < 0 or cls.lunch_break_slot >= ts.periods_per_day:
            errors.append(
                f"Class '{cls_name}' lunch_break_slot={cls.lunch_break_slot} "
                f"is out of range [0, {ts.periods_per_day - 1}]"
            )

    for bp in ts.break_periods:
        if bp < 0 or bp >= ts.periods_per_day:
            errors.append(f"Break period {bp} is out of range [0, {ts.periods_per_day - 1}]")

    # Teacher unavailable slots must be valid
    for t_name, teacher in dataset.teachers.items():
        for day, period in teacher.unavailable_slots:
            if not ts.is_valid_slot(day, period):
                warnings.append(
                    f"Teacher '{t_name}' unavailable slot ({day},{period}) is out of range"
                )

    # Room type matching: every lab subject must have at least one lab room fitting the class
    for cls_name, cls in dataset.classes.items():
        for sc in cls.subjects:
            if sc not in dataset.subjects:
                continue
            subj = dataset.subjects[sc]
            matching_rooms = [
                r for r in dataset.rooms.values()
                if r.room_type == ("lab" if subj.subject_type == "lab" else "classroom")
                and r.capacity >= cls.strength
            ]
            if not matching_rooms:
                errors.append(
                    f"Class '{cls_name}' (strength={cls.strength}) has no "
                    f"{'lab' if subj.subject_type == 'lab' else 'classroom'} room "
                    f"large enough for subject '{sc}' ({subj.subject_type})"
                )

    # ── Solvability pre-check ──

    # Available slots per class (after lunch and breaks)
    usable_periods = ts.periods_per_day - len(ts.break_periods)
    # Note: lunch is per-class, counted separately below

    # Per-class hours check
    for cls_name, cls in dataset.classes.items():
        total_hours = 0
        for sc in cls.subjects:
            if sc in dataset.subjects:
                total_hours += dataset.subjects[sc].weekly_hours
        # Available = working_days * (periods - breaks - 1 lunch)
        available = ts.working_days * (usable_periods - 1)  # -1 for lunch
        if total_hours > available:
            errors.append(
                f"Class '{cls_name}' needs {total_hours} hours/week but only "
                f"{available} slots available (after lunch and breaks). "
                f"Over by {total_hours - available}."
            )

    # Per-teacher hours check
    for t_name, teacher in dataset.teachers.items():
        # Count how many hours this teacher is needed for
        needed = 0
        for cls in dataset.classes.values():
            for sc in cls.subjects:
                if sc in dataset.subjects and sc in teacher.subjects:
                    # Check if this teacher is the only option or will be assigned
                    eligible = dataset.subject_teachers.get(sc, [])
                    if len(eligible) > 0:
                        # Rough estimate: divide hours among eligible teachers
                        needed += dataset.subjects[sc].weekly_hours / len(eligible)

        # Available slots for this teacher
        total_slots = ts.working_days * usable_periods
        unavail_count = len(teacher.unavailable_slots)
        available = min(teacher.max_weekly_load, total_slots - unavail_count)

        if needed > available * 1.2:  # Allow 20% buffer since estimate is rough
            warnings.append(
                f"Teacher '{t_name}' may be overloaded: estimated need ~{needed:.0f} hours, "
                f"available {available} slots (max_load={teacher.max_weekly_load})"
            )

    # Total room-slot check (per room type)
    for rtype in ("classroom", "lab"):
        rooms_of_type = [r for r in dataset.rooms.values() if r.room_type == rtype]
        total_room_slots = len(rooms_of_type) * ts.working_days * usable_periods

        needed_slots = 0
        for cls in dataset.classes.values():
            for sc in cls.subjects:
                if sc in dataset.subjects:
                    subj = dataset.subjects[sc]
                    expected_type = "lab" if subj.subject_type == "lab" else "classroom"
                    if expected_type == rtype:
                        needed_slots += subj.weekly_hours

        if needed_slots > total_room_slots:
            errors.append(
                f"Total {rtype} hours needed ({needed_slots}) exceed available "
                f"{rtype} room-slots ({total_room_slots}). Over by {needed_slots - total_room_slots}."
            )
        else:
            utilisation = (needed_slots / total_room_slots * 100) if total_room_slots > 0 else 0
            if utilisation > 85:
                warnings.append(
                    f"{rtype.title()} utilisation is {utilisation:.0f}% "
                    f"({needed_slots}/{total_room_slots} slots) — may be tight"
                )

    if errors:
        logger.error("Validation failed with %d errors", len(errors))
    else:
        logger.info("Validation passed (%d warnings)", len(warnings))

    return errors, warnings
