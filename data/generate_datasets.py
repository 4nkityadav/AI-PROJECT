"""
generate_datasets.py — Create and verify both sample datasets.

Creates:
  - Small: 3 classes, 6 teachers, 4 rooms, 5 days x 6 periods
  - Large: 8 classes, 15 teachers, 8 rooms, 5 days x 7 periods

Uses realistic Indian college subject names. Includes teacher
unavailable slots and preferences, varied class strengths, and
a mix of room capacities.

After generating, verifies each dataset by:
  1. Running validation
  2. Producing a timetable with backtracking (to prove solvability)
  3. Computing utilisation percentages
"""

import json
import os
import sys
import random
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.loader import parse_dataset
from core.validator import validate_dataset
from core.teacher_assign import assign_teachers_and_create_sessions
from core.backtracking import solve_backtracking
from core.constraints import count_violations
from core.models import SolverConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_small_dataset() -> dict:
    """
    Small dataset: 3 classes, 6 teachers, 4 rooms, 5 days x 6 periods.
    Total theory hours needed: ~39 sessions
    Available classroom slots: 3 rooms × 5 days × 5 usable periods = 75
    Available lab slots: 1 room × 5 days × 5 usable periods = 25
    """
    return {
        "subjects": [
            {"code": "CS201", "name": "Data Structures", "weekly_hours": 3, "type": "theory"},
            {"code": "CS202", "name": "Database Systems", "weekly_hours": 3, "type": "theory"},
            {"code": "CS203", "name": "Operating Systems", "weekly_hours": 3, "type": "theory"},
            {"code": "MA201", "name": "Discrete Mathematics", "weekly_hours": 3, "type": "theory"},
            {"code": "PH201", "name": "Physics", "weekly_hours": 2, "type": "theory"},
            {"code": "CS204", "name": "DS Lab", "weekly_hours": 2, "type": "lab"},
            {"code": "CS205", "name": "DBMS Lab", "weekly_hours": 2, "type": "lab"},
        ],
        "teachers": [
            {"name": "Dr. Sharma", "subjects": ["CS201", "CS203"],
             "unavailable_slots": [[0, 5]], "max_weekly_load": 18, "avoid_periods": [0]},
            {"name": "Dr. Gupta", "subjects": ["CS202", "CS205"],
             "unavailable_slots": [[4, 0]], "max_weekly_load": 18, "avoid_periods": []},
            {"name": "Dr. Kumar", "subjects": ["MA201"],
             "unavailable_slots": [], "max_weekly_load": 15, "avoid_periods": [0]},
            {"name": "Dr. Singh", "subjects": ["PH201"],
             "unavailable_slots": [[2, 4]], "max_weekly_load": 12, "avoid_periods": []},
            {"name": "Prof. Rao", "subjects": ["CS204"],
             "unavailable_slots": [], "max_weekly_load": 12, "avoid_periods": []},
            {"name": "Prof. Jain", "subjects": ["CS201", "MA201"],
             "unavailable_slots": [[1, 0]], "max_weekly_load": 15, "avoid_periods": [0]},
        ],
        "classes": [
            {"name": "CSE-A", "strength": 40,
             "subjects": ["CS201", "CS202", "MA201", "PH201", "CS204"],
             "lunch_break_slot": 2},
            {"name": "CSE-B", "strength": 35,
             "subjects": ["CS201", "CS203", "MA201", "PH201", "CS205"],
             "lunch_break_slot": 2},
            {"name": "CSE-C", "strength": 45,
             "subjects": ["CS202", "CS203", "MA201", "CS204", "CS205"],
             "lunch_break_slot": 2},
        ],
        "rooms": [
            {"name": "Room-101", "capacity": 50, "type": "classroom"},
            {"name": "Room-102", "capacity": 45, "type": "classroom"},
            {"name": "Room-103", "capacity": 40, "type": "classroom"},
            {"name": "Lab-1", "capacity": 50, "type": "lab"},
        ],
        "time_structure": {
            "working_days": 5,
            "periods_per_day": 6,
            "break_periods": []
        }
    }


def get_medium_dataset() -> dict:
    """
    Medium dataset: 5 classes, 12 teachers, 8 rooms, 5 days x 6 periods.
    Realistic engineering department (CSE, IT, AI-DS, ECE) with balanced theory and lab courses.
    """
    return {
        "name": "Engineering Department (Medium Benchmark)",
        "description": "Realistic collegiate Computer Science & Engineering department with 5 class cohorts, 12 faculty members, 8 rooms (including specialized software/hardware labs), and balanced theory & lab sessions.",
        "subjects": [
            {"code": "CS301", "name": "Database Management Systems", "weekly_hours": 3, "type": "theory"},
            {"code": "CS302", "name": "Computer Networks & Security", "weekly_hours": 3, "type": "theory"},
            {"code": "CS303", "name": "Design & Analysis of Algorithms", "weekly_hours": 3, "type": "theory"},
            {"code": "CS304", "name": "Operating Systems & Kernel Design", "weekly_hours": 3, "type": "theory"},
            {"code": "AI201", "name": "Machine Learning Foundations", "weekly_hours": 3, "type": "theory"},
            {"code": "EC202", "name": "Microprocessors & Embedded Systems", "weekly_hours": 3, "type": "theory"},
            {"code": "MA301", "name": "Applied Probability & Statistics", "weekly_hours": 3, "type": "theory"},
            {"code": "HS301", "name": "Professional Ethics & Communication", "weekly_hours": 2, "type": "theory"},
            {"code": "CS305L", "name": "Database Systems Laboratory", "weekly_hours": 2, "type": "lab"},
            {"code": "CS306L", "name": "Computer Networks Laboratory", "weekly_hours": 2, "type": "lab"},
            {"code": "AI202L", "name": "Machine Learning & GPU Lab", "weekly_hours": 2, "type": "lab"},
            {"code": "EC203L", "name": "Embedded Hardware Laboratory", "weekly_hours": 2, "type": "lab"},
        ],
        "teachers": [
            {"name": "Dr. Alan Turing", "subjects": ["CS301", "CS305L"], "unavailable_slots": [[0, 5]], "max_weekly_load": 18, "avoid_periods": [0]},
            {"name": "Dr. Barbara Liskov", "subjects": ["CS303", "CS304"], "unavailable_slots": [], "max_weekly_load": 18, "avoid_periods": []},
            {"name": "Dr. Claude Shannon", "subjects": ["CS302", "EC202"], "unavailable_slots": [[2, 5]], "max_weekly_load": 18, "avoid_periods": []},
            {"name": "Dr. Geoffrey Hinton", "subjects": ["AI201", "AI202L"], "unavailable_slots": [], "max_weekly_load": 18, "avoid_periods": []},
            {"name": "Prof. Grace Hopper", "subjects": ["CS301", "CS304"], "unavailable_slots": [], "max_weekly_load": 18, "avoid_periods": []},
            {"name": "Prof. Donald Knuth", "subjects": ["CS303", "MA301"], "unavailable_slots": [], "max_weekly_load": 18, "avoid_periods": [0]},
            {"name": "Prof. Linus Torvalds", "subjects": ["CS304", "CS306L"], "unavailable_slots": [[4, 0]], "max_weekly_load": 18, "avoid_periods": []},
            {"name": "Prof. Radia Perlman", "subjects": ["CS302", "CS306L"], "unavailable_slots": [], "max_weekly_load": 18, "avoid_periods": []},
            {"name": "Dr. John von Neumann", "subjects": ["MA301", "EC202"], "unavailable_slots": [], "max_weekly_load": 18, "avoid_periods": []},
            {"name": "Prof. Margaret Hamilton", "subjects": ["HS301", "CS305L"], "unavailable_slots": [], "max_weekly_load": 16, "avoid_periods": []},
            {"name": "Dr. Andrew Ng", "subjects": ["AI201", "AI202L"], "unavailable_slots": [], "max_weekly_load": 18, "avoid_periods": []},
            {"name": "Prof. Ken Thompson", "subjects": ["EC202", "EC203L"], "unavailable_slots": [], "max_weekly_load": 16, "avoid_periods": []},
        ],
        "classes": [
            {"name": "CSE-3A", "strength": 55, "subjects": ["CS301", "CS302", "CS303", "MA301", "CS305L"], "lunch_break_slot": 2},
            {"name": "CSE-3B", "strength": 52, "subjects": ["CS301", "CS302", "CS304", "HS301", "CS306L"], "lunch_break_slot": 2},
            {"name": "IT-3A", "strength": 48, "subjects": ["CS302", "CS303", "CS304", "AI201", "CS306L"], "lunch_break_slot": 3},
            {"name": "AI-DS-2A", "strength": 50, "subjects": ["AI201", "CS301", "MA301", "HS301", "AI202L"], "lunch_break_slot": 2},
            {"name": "ECE-2A", "strength": 45, "subjects": ["EC202", "CS302", "MA301", "HS301", "EC203L"], "lunch_break_slot": 3},
        ],
        "rooms": [
            {"name": "LH-101", "capacity": 70, "type": "classroom"},
            {"name": "LH-102", "capacity": 65, "type": "classroom"},
            {"name": "CR-201", "capacity": 60, "type": "classroom"},
            {"name": "CR-202", "capacity": 55, "type": "classroom"},
            {"name": "Lab-DBMS", "capacity": 60, "type": "lab"},
            {"name": "Lab-Networks", "capacity": 55, "type": "lab"},
            {"name": "Lab-AI", "capacity": 60, "type": "lab"},
            {"name": "Lab-Embedded", "capacity": 50, "type": "lab"},
        ],
        "time_structure": {
            "working_days": 5,
            "periods_per_day": 6,
            "break_periods": []
        }
    }


def generate_custom_dataset(
    num_classes: int = 4,
    num_teachers: int = 8,
    num_rooms: int = 6,
    days: int = 5,
    periods_per_day: int = 6,
) -> dict:
    """
    Generate a solvable, customized synthetic university timetable dataset
    matching the exact specifications requested by the user.
    """
    import math
    subject_names = [
        ("CS101", "Programming Fundamentals", 3, "theory"),
        ("CS102", "Data Structures", 3, "theory"),
        ("CS103", "Database Systems", 3, "theory"),
        ("CS104", "Computer Networks", 3, "theory"),
        ("CS105", "Operating Systems", 3, "theory"),
        ("MA101", "Engineering Math", 3, "theory"),
        ("EC101", "Digital Electronics", 2, "theory"),
        ("HS101", "Communication Skills", 2, "theory"),
        ("CS106", "Programming Lab", 2, "lab"),
        ("CS107", "Database Lab", 2, "lab"),
        ("CS108", "Networks Lab", 2, "lab"),
    ]

    selected_subjects = subject_names[:max(5, min(len(subject_names), num_classes + 3))]
    subjects_data = [
        {"code": code, "name": name, "weekly_hours": hrs, "type": stype}
        for code, name, hrs, stype in selected_subjects
    ]

    # Assign teachers to subjects
    teachers_data = []
    subject_codes = [s["code"] for s in subjects_data]
    for i in range(num_teachers):
        t_subjs = [subject_codes[(i + j) % len(subject_codes)] for j in range(2)]
        unavail = []
        if i % 3 == 0:
            unavail.append([i % days, periods_per_day - 1])
        teachers_data.append({
            "name": f"Faculty-{chr(65 + i)}",
            "subjects": t_subjs,
            "unavailable_slots": unavail,
            "max_weekly_load": 20,
            "avoid_periods": [0] if i % 2 == 0 else []
        })

    # Classes
    classes_data = []
    for i in range(num_classes):
        # Pick 4 theory + 1 lab
        cls_subjs = [s["code"] for s in subjects_data if s["type"] == "theory"][:4]
        labs = [s["code"] for s in subjects_data if s["type"] == "lab"]
        if labs:
            cls_subjs.append(labs[i % len(labs)])
        classes_data.append({
            "name": f"Batch-{chr(65 + i)}",
            "strength": 40 + (i % 3) * 5,
            "subjects": cls_subjs,
            "lunch_break_slot": periods_per_day // 2 - 1,
        })

    # Rooms
    rooms_data = []
    num_labs = max(1, num_rooms // 3)
    num_classrooms = max(1, num_rooms - num_labs)
    for i in range(num_classrooms):
        rooms_data.append({"name": f"Room-{101 + i}", "capacity": 55, "type": "classroom"})
    for i in range(num_labs):
        rooms_data.append({"name": f"Lab-{chr(65 + i)}", "capacity": 55, "type": "lab"})

    return {
        "subjects": subjects_data,
        "teachers": teachers_data,
        "classes": classes_data,
        "rooms": rooms_data,
        "time_structure": {
            "working_days": days,
            "periods_per_day": periods_per_day,
            "break_periods": []
        }
    }


def get_large_dataset() -> dict:
    """
    Large dataset: 8 classes, 15 teachers, 8 rooms, 5 days x 7 periods.
    Designed to be solvable but challenging.
    """
    return {
        "subjects": [
            {"code": "CS301", "name": "Algorithms", "weekly_hours": 3, "type": "theory"},
            {"code": "CS302", "name": "Computer Networks", "weekly_hours": 3, "type": "theory"},
            {"code": "CS303", "name": "Software Engineering", "weekly_hours": 3, "type": "theory"},
            {"code": "CS304", "name": "Machine Learning", "weekly_hours": 3, "type": "theory"},
            {"code": "CS305", "name": "Web Development", "weekly_hours": 2, "type": "theory"},
            {"code": "CS306", "name": "Cyber Security", "weekly_hours": 2, "type": "theory"},
            {"code": "MA301", "name": "Linear Algebra", "weekly_hours": 3, "type": "theory"},
            {"code": "MA302", "name": "Probability", "weekly_hours": 2, "type": "theory"},
            {"code": "EC301", "name": "Digital Electronics", "weekly_hours": 2, "type": "theory"},
            {"code": "CS307", "name": "Algo Lab", "weekly_hours": 2, "type": "lab"},
            {"code": "CS308", "name": "Networks Lab", "weekly_hours": 2, "type": "lab"},
            {"code": "CS309", "name": "ML Lab", "weekly_hours": 2, "type": "lab"},
            {"code": "CS310", "name": "Web Lab", "weekly_hours": 2, "type": "lab"},
        ],
        "teachers": [
            {"name": "Dr. Agarwal", "subjects": ["CS301", "CS307"],
             "unavailable_slots": [[0, 6]], "max_weekly_load": 20, "avoid_periods": [0]},
            {"name": "Dr. Banerjee", "subjects": ["CS302", "CS308"],
             "unavailable_slots": [], "max_weekly_load": 20, "avoid_periods": []},
            {"name": "Dr. Choudhary", "subjects": ["CS303"],
             "unavailable_slots": [[4, 0]], "max_weekly_load": 18, "avoid_periods": [0]},
            {"name": "Dr. Das", "subjects": ["CS304", "CS309"],
             "unavailable_slots": [], "max_weekly_load": 20, "avoid_periods": []},
            {"name": "Dr. Emani", "subjects": ["CS305", "CS310"],
             "unavailable_slots": [[2, 5]], "max_weekly_load": 18, "avoid_periods": []},
            {"name": "Dr. Fernandes", "subjects": ["CS306"],
             "unavailable_slots": [], "max_weekly_load": 15, "avoid_periods": [0]},
            {"name": "Dr. Ghosh", "subjects": ["MA301"],
             "unavailable_slots": [[1, 0]], "max_weekly_load": 20, "avoid_periods": [0]},
            {"name": "Dr. Hussain", "subjects": ["MA302"],
             "unavailable_slots": [], "max_weekly_load": 15, "avoid_periods": []},
            {"name": "Dr. Iyer", "subjects": ["EC301"],
             "unavailable_slots": [[3, 6]], "max_weekly_load": 15, "avoid_periods": []},
            {"name": "Prof. Joshi", "subjects": ["CS301", "CS303"],
             "unavailable_slots": [], "max_weekly_load": 18, "avoid_periods": []},
            {"name": "Prof. Kapoor", "subjects": ["CS302", "CS304"],
             "unavailable_slots": [[0, 0]], "max_weekly_load": 18, "avoid_periods": [0]},
            {"name": "Prof. Lal", "subjects": ["MA301", "MA302"],
             "unavailable_slots": [], "max_weekly_load": 18, "avoid_periods": []},
            {"name": "Prof. Mehta", "subjects": ["CS307", "CS308"],
             "unavailable_slots": [], "max_weekly_load": 16, "avoid_periods": []},
            {"name": "Prof. Nair", "subjects": ["CS309", "CS310"],
             "unavailable_slots": [[4, 5]], "max_weekly_load": 16, "avoid_periods": []},
            {"name": "Prof. Pandey", "subjects": ["CS305", "CS306", "EC301"],
             "unavailable_slots": [], "max_weekly_load": 18, "avoid_periods": []},
        ],
        "classes": [
            {"name": "CS-3A", "strength": 50, "subjects": ["CS301", "CS302", "MA301", "CS305", "CS307"], "lunch_break_slot": 3},
            {"name": "CS-3B", "strength": 45, "subjects": ["CS301", "CS303", "MA301", "CS306", "CS308"], "lunch_break_slot": 3},
            {"name": "CS-3C", "strength": 50, "subjects": ["CS302", "CS304", "MA302", "EC301", "CS309"], "lunch_break_slot": 3},
            {"name": "CS-3D", "strength": 40, "subjects": ["CS303", "CS304", "MA301", "CS305", "CS310"], "lunch_break_slot": 3},
            {"name": "CS-4A", "strength": 45, "subjects": ["CS301", "CS304", "MA302", "CS306", "CS307"], "lunch_break_slot": 3},
            {"name": "CS-4B", "strength": 50, "subjects": ["CS302", "CS303", "MA301", "EC301", "CS308"], "lunch_break_slot": 3},
            {"name": "CS-4C", "strength": 40, "subjects": ["CS301", "CS305", "MA302", "CS306", "CS309"], "lunch_break_slot": 3},
            {"name": "CS-4D", "strength": 45, "subjects": ["CS303", "CS304", "MA301", "EC301", "CS310"], "lunch_break_slot": 3},
        ],
        "rooms": [
            {"name": "Hall-A", "capacity": 60, "type": "classroom"},
            {"name": "Hall-B", "capacity": 55, "type": "classroom"},
            {"name": "Hall-C", "capacity": 50, "type": "classroom"},
            {"name": "Hall-D", "capacity": 50, "type": "classroom"},
            {"name": "CompLab-1", "capacity": 50, "type": "lab"},
            {"name": "CompLab-2", "capacity": 50, "type": "lab"},
            {"name": "CompLab-3", "capacity": 45, "type": "lab"},
            {"name": "CompLab-4", "capacity": 40, "type": "lab"},
        ],
        "time_structure": {
            "working_days": 5,
            "periods_per_day": 7,
            "break_periods": []
        }
    }


def save_as_csv(data: dict, out_dir: str):
    """Save dataset as separate CSV files."""
    import csv
    os.makedirs(out_dir, exist_ok=True)

    # Subjects
    with open(os.path.join(out_dir, "subjects.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["code", "name", "weekly_hours", "type"])
        w.writeheader()
        w.writerows(data["subjects"])

    # Teachers
    with open(os.path.join(out_dir, "teachers.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "subjects", "unavailable_slots", "max_weekly_load", "avoid_periods"])
        for t in data["teachers"]:
            subjs = ";".join(t["subjects"])
            unavail = ";".join(f"{s[0]},{s[1]}" for s in t["unavailable_slots"])
            avoid = ";".join(str(p) for p in t.get("avoid_periods", []))
            w.writerow([t["name"], subjs, unavail, t["max_weekly_load"], avoid])

    # Classes
    with open(os.path.join(out_dir, "classes.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "strength", "subjects", "lunch_break_slot"])
        for c in data["classes"]:
            subjs = ";".join(c["subjects"])
            w.writerow([c["name"], c["strength"], subjs, c["lunch_break_slot"]])

    # Rooms
    with open(os.path.join(out_dir, "rooms.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "capacity", "type"])
        w.writeheader()
        w.writerows(data["rooms"])


def verify_dataset(name: str, data: dict):
    """Verify a dataset by validating and solving it."""
    print(f"\n{'-'*50}")
    print(f"Verifying {name} dataset...")

    dataset = parse_dataset(data)
    errors, warnings = validate_dataset(dataset)

    if errors:
        print(f"  ERRORS:")
        for e in errors:
            print(f"    [X] {e}")
        return False

    if warnings:
        print(f"  Warnings:")
        for w in warnings:
            print(f"    [!] {w}")

    # Create sessions and solve
    config = SolverConfig(seed=42, time_limit=30.0, max_nodes=200000,
                          use_mrv=True, use_degree=True, use_forward_checking=True)
    assign_teachers_and_create_sessions(dataset, config)

    print(f"  Sessions: {len(dataset.sessions)}")

    random.seed(42)
    result = solve_backtracking(dataset, config)

    if result.success:
        report = count_violations(result.timetable, dataset, config)
        print(f"  [OK] Solvable! Hard violations: {report.hard_count}, Soft penalty: {report.soft_penalty:.1f}")
        print(f"  Time: {result.time_seconds:.4f}s, Nodes: {result.nodes_or_iterations}")

        # Calculate utilisation
        ts = dataset.time_structure
        usable = ts.periods_per_day - len(ts.break_periods) - 1  # minus lunch
        for rtype in ("classroom", "lab"):
            rooms_of_type = [r for r in dataset.rooms.values() if r.room_type == rtype]
            total_slots = len(rooms_of_type) * ts.working_days * usable
            used = sum(1 for s, v in result.timetable.assignment.items()
                       if v and s.subject_code in dataset.subjects
                       and (("lab" if dataset.subjects[s.subject_code].subject_type == "lab" else "classroom") == rtype))
            pct = (used / total_slots * 100) if total_slots > 0 else 0
            print(f"  {rtype.title()} utilisation: {pct:.0f}% ({used}/{total_slots})")
        return True
    else:
        print(f"  [FAIL] Could not solve! Status: {result.status}")
        print(f"  Time: {result.time_seconds:.4f}s, Nodes: {result.nodes_or_iterations}")
        return False


if __name__ == "__main__":
    data_dir = os.path.dirname(os.path.abspath(__file__))

    # Generate small dataset
    small = get_small_dataset()
    with open(os.path.join(data_dir, "small.json"), "w") as f:
        json.dump(small, f, indent=2)
    save_as_csv(small, os.path.join(data_dir, "csv_small"))

    # Generate medium dataset
    medium = get_medium_dataset()
    with open(os.path.join(data_dir, "medium.json"), "w") as f:
        json.dump(medium, f, indent=2)
    save_as_csv(medium, os.path.join(data_dir, "csv_medium"))

    # Generate large dataset
    large = get_large_dataset()
    with open(os.path.join(data_dir, "large.json"), "w") as f:
        json.dump(large, f, indent=2)
    save_as_csv(large, os.path.join(data_dir, "csv_large"))

    print("Datasets saved to JSON and CSV.")

    # Verify all three
    ok_small = verify_dataset("Small", small)
    ok_medium = verify_dataset("Medium", medium)
    ok_large = verify_dataset("Large", large)

    if ok_small and ok_medium and ok_large:
        print(f"\n{'='*50}")
        print("All three datasets (Small, Medium, Large) verified successfully!")
    else:
        print(f"\n{'='*50}")
        print("SOME DATASETS FAILED VERIFICATION")
        sys.exit(1)

