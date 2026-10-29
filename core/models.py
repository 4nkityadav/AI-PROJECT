"""
models.py — Dataclasses for every entity in the timetable problem.

Design decisions:
- We use frozen dataclasses where the object should not change after creation
  (Subject, Room) so they can be hashed and used as dict keys.
- Session is the CSP *variable*. Its domain is (day, period, room) triples.
- Timetable wraps a dict[Session, tuple] assignment plus metadata.
- Dataset bundles all input data so every function signature stays clean.
- Result is the standard return type for every solver.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ────────────────────────────────────────────
# Input entities
# ────────────────────────────────────────────

@dataclass(frozen=True)
class Subject:
    """A course offered by the college."""
    code: str                     # unique, e.g. "CS201"
    name: str                     # human-readable, e.g. "Data Structures"
    weekly_hours: int             # how many 1-period slots per week
    subject_type: str             # "theory" or "lab"

    def __post_init__(self):
        if self.subject_type not in ("theory", "lab"):
            raise ValueError(f"Subject type must be 'theory' or 'lab', got '{self.subject_type}'")
        if self.weekly_hours < 1:
            raise ValueError(f"weekly_hours must be >= 1, got {self.weekly_hours}")


@dataclass
class Teacher:
    """A teacher who can teach one or more subjects."""
    name: str                                       # unique identifier
    subjects: list[str]                             # subject codes
    unavailable_slots: list[tuple[int, int]]        # (day, period) pairs where busy
    max_weekly_load: int                            # upper bound on periods per week
    avoid_periods: list[int] = field(default_factory=list)  # S4: prefer not to teach here

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if not isinstance(other, Teacher):
            return NotImplemented
        return self.name == other.name


@dataclass
class ClassBatch:
    """A class / batch of students."""
    name: str                     # e.g. "CSE-A"
    strength: int                 # number of students
    subjects: list[str]           # subject codes this class takes
    lunch_break_slot: int         # period index that is lunch every day

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if not isinstance(other, ClassBatch):
            return NotImplemented
        return self.name == other.name


@dataclass(frozen=True)
class Room:
    """A physical room (classroom or lab)."""
    name: str                     # e.g. "Room-101"
    capacity: int                 # max students
    room_type: str                # "classroom" or "lab"

    def __post_init__(self):
        if self.room_type not in ("classroom", "lab"):
            raise ValueError(f"room_type must be 'classroom' or 'lab', got '{self.room_type}'")


@dataclass
class TimeStructure:
    """Describes the shape of the weekly timetable."""
    working_days: int             # e.g. 5
    periods_per_day: int          # e.g. 6
    break_periods: list[int] = field(default_factory=list)  # global break period indices

    @property
    def day_names(self) -> list[str]:
        names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return names[:self.working_days]

    def is_valid_slot(self, day: int, period: int) -> bool:
        return 0 <= day < self.working_days and 0 <= period < self.periods_per_day


# ────────────────────────────────────────────
# CSP variable
# ────────────────────────────────────────────

@dataclass(frozen=True)
class Session:
    """
    One lecture session — this is a single CSP variable.

    Example: (ClassA, CS201, session_index=1, teacher=Dr.Gupta)
    The domain of a Session is a set of (day, period, room_name) triples.
    For lab blocks (block_size > 1), the period is the START period and the
    session occupies [period, period + block_size - 1].
    """
    class_name: str
    subject_code: str
    session_index: int           # 0-based among sessions for this (class, subject)
    teacher_name: str
    block_size: int = 1          # 1 for theory, 2 for a 2-period lab block

    def label(self) -> str:
        """Short human-readable label for display."""
        return f"{self.class_name} | {self.subject_code} #{self.session_index + 1}"


# ────────────────────────────────────────────
# Timetable and result
# ────────────────────────────────────────────

@dataclass
class Timetable:
    """
    A (possibly partial) assignment of sessions to (day, period, room) slots.
    locked_sessions tracks sessions the user has pinned.
    """
    assignment: dict  # Session -> (day: int, period: int, room_name: str) or None
    locked_sessions: set = field(default_factory=set)  # set of Session keys that are pinned

    def get_slot(self, session: Session) -> Optional[tuple[int, int, str]]:
        return self.assignment.get(session)

    def set_slot(self, session: Session, day: int, period: int, room: str):
        self.assignment[session] = (day, period, room)

    def is_complete(self) -> bool:
        return all(v is not None for v in self.assignment.values())


@dataclass
class ViolationDetail:
    """One specific constraint violation."""
    code: str           # e.g. "H1", "S3"
    message: str        # human-readable description
    sessions: list      # sessions involved (Session objects or labels)
    day: int = -1
    period: int = -1


@dataclass
class ViolationReport:
    """Full breakdown of all violations in a timetable."""
    hard_violations: list[ViolationDetail] = field(default_factory=list)
    soft_violations: list[ViolationDetail] = field(default_factory=list)
    hard_count: int = 0
    soft_penalty: int = 0
    cost: float = 0.0       # 1000 * hard_count + soft_penalty
    per_code: dict = field(default_factory=dict)  # e.g. {"H1": 2, "S1": 5}


@dataclass
class SolverConfig:
    """Configuration passed to every solver."""
    seed: int = 42
    time_limit: float = 60.0           # seconds
    max_nodes: int = 200_000           # for backtracking
    max_iterations: int = 20_000       # for local search
    # Backtracking heuristic flags
    use_mrv: bool = True
    use_degree: bool = True
    use_lcv: bool = False
    use_forward_checking: bool = True
    use_ac3: bool = False
    # Min-Conflicts
    random_walk_prob: float = 0.02
    restart_after: int = 2000          # restart if no improvement for this many iterations
    # Simulated Annealing
    sa_initial_temp: float = 100.0
    sa_cooling_alpha: float = 0.995
    sa_iterations_per_temp: int = 50
    sa_min_temp: float = 0.01
    # Soft constraint weights
    weight_s1: float = 2.0   # gaps
    weight_s2: float = 2.0   # same subject twice a day
    weight_s3: float = 3.0   # lab consecutiveness
    weight_s4: float = 1.0   # teacher preferences
    weight_s5: float = 2.0   # >2 consecutive teacher lectures
    # Lab mode
    lab_block_size: int = 2
    lab_mode: str = "block"  # "block" or "split"


@dataclass
class Result:
    """Standard return type for every solver."""
    timetable: Optional[Timetable]
    success: bool
    hard_violations: int
    soft_penalty: float
    cost: float
    time_seconds: float
    nodes_or_iterations: int
    cost_history: list[float] = field(default_factory=list)
    status: str = "solved"      # "solved", "timeout", "failed"
    algorithm: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class Dataset:
    """
    Bundles all input data so function signatures stay clean.
    Dictionaries are keyed by name/code for O(1) lookup.
    """
    subjects: dict[str, Subject]          # code -> Subject
    teachers: dict[str, Teacher]          # name -> Teacher
    classes: dict[str, ClassBatch]        # name -> ClassBatch
    rooms: dict[str, Room]                # name -> Room
    time_structure: TimeStructure
    sessions: list[Session] = field(default_factory=list)
    # Precomputed for CSP
    subject_teachers: dict[str, list[str]] = field(default_factory=dict)  # subj_code -> [teacher_names]

    def build_subject_teachers(self):
        """Compute which teachers can teach each subject."""
        self.subject_teachers = {}
        for t_name, teacher in self.teachers.items():
            for sc in teacher.subjects:
                if sc not in self.subject_teachers:
                    self.subject_teachers[sc] = []
                self.subject_teachers[sc].append(t_name)
