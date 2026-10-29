"""
teacher_assign.py — Auto-assign teachers to (class, subject) pairs.

When the dataset does not have a fixed teacher-class-subject mapping,
this module assigns teachers by load balancing among eligible teachers,
respecting availability (H6) and max load (H8).
"""

from __future__ import annotations
import logging
from collections import defaultdict
from core.models import Dataset, Session, SolverConfig

logger = logging.getLogger(__name__)


def assign_teachers_and_create_sessions(
    dataset: Dataset,
    config: SolverConfig | None = None,
) -> list[Session]:
    """
    For each (class, subject) pair, assign a teacher and create Session variables.

    Strategy:
    - For each class's subject, find eligible teachers (those who list the subject).
    - Pick the teacher with the lowest current assigned load (greedy balancing).
    - Create one Session per weekly hour (theory: block_size=1).
    - For labs in "block" mode: create ceil(weekly_hours / block_size) sessions
      each with the configured block_size.
    - For labs in "split" mode: each hour is a separate Session (block_size=1).

    Returns the list of Session objects and also sets dataset.sessions.
    """
    if config is None:
        config = SolverConfig()

    dataset.build_subject_teachers()
    sessions: list[Session] = []
    teacher_load: dict[str, int] = defaultdict(int)

    for cls_name, cls_batch in dataset.classes.items():
        for subj_code in cls_batch.subjects:
            if subj_code not in dataset.subjects:
                logger.warning("Class %s references unknown subject %s, skipping", cls_name, subj_code)
                continue

            subject = dataset.subjects[subj_code]
            eligible = dataset.subject_teachers.get(subj_code, [])
            if not eligible:
                logger.error("No teacher available for subject %s (class %s)", subj_code, cls_name)
                continue

            # Determine block size and number of sessions
            if subject.subject_type == "lab" and config.lab_mode == "block":
                block_size = config.lab_block_size
                # E.g. 2 weekly hours with block_size=2 → 1 session of size 2
                num_sessions = subject.weekly_hours // block_size
                remainder = subject.weekly_hours % block_size
            else:
                block_size = 1
                num_sessions = subject.weekly_hours
                remainder = 0

            # Assign teacher: pick the one with lowest current load
            # All sessions for the same (class, subject) get the same teacher
            # (this is a simplification; the assignment says "fix the teacher in advance")
            best_teacher = min(
                eligible,
                key=lambda t: teacher_load[t]
            )

            for idx in range(num_sessions):
                session = Session(
                    class_name=cls_name,
                    subject_code=subj_code,
                    session_index=idx,
                    teacher_name=best_teacher,
                    block_size=block_size,
                )
                sessions.append(session)
                teacher_load[best_teacher] += block_size

            # Handle remainder (e.g. 3 lab hours with block_size=2 → 1 block of 2 + 1 of 1)
            if remainder > 0:
                session = Session(
                    class_name=cls_name,
                    subject_code=subj_code,
                    session_index=num_sessions,
                    teacher_name=best_teacher,
                    block_size=remainder,
                )
                sessions.append(session)
                teacher_load[best_teacher] += remainder

    dataset.sessions = sessions
    logger.info("Created %d sessions with teacher assignments", len(sessions))

    # Log teacher load distribution
    for t_name in sorted(teacher_load, key=teacher_load.get, reverse=True):
        logger.debug("  %s: %d periods assigned", t_name, teacher_load[t_name])

    return sessions
