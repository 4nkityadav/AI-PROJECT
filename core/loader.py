"""
loader.py — Load datasets from JSON or CSV files.

Converts raw dicts/DataFrames into the typed Dataset object.
Handles both JSON (single file) and CSV (one file per entity) formats.
"""

from __future__ import annotations
import json
import csv
import io
import logging
from typing import Any

from core.models import (
    Subject, Teacher, ClassBatch, Room, TimeStructure, Dataset
)

logger = logging.getLogger(__name__)


def load_json(source) -> dict:
    """
    Load raw data from a JSON source.
    source can be a file path (str), a file-like object, or a dict.
    """
    if isinstance(source, dict):
        return source
    if isinstance(source, str):
        with open(source, "r", encoding="utf-8") as f:
            return json.load(f)
    # file-like (e.g. Streamlit UploadedFile)
    content = source.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    return json.loads(content)


def parse_dataset(raw: dict) -> Dataset:
    """
    Parse a raw dictionary (from JSON or constructed from CSV) into a Dataset.
    Raises ValueError with clear messages if required fields are missing.
    """
    errors = []

    # --- Subjects ---
    subjects = {}
    for i, s in enumerate(raw.get("subjects", [])):
        try:
            subj = Subject(
                code=str(s["code"]).strip(),
                name=str(s["name"]).strip(),
                weekly_hours=int(s["weekly_hours"]),
                subject_type=str(s["type"]).strip().lower(),
            )
            subjects[subj.code] = subj
        except (KeyError, ValueError) as e:
            errors.append(f"Subject #{i+1}: {e}")

    # --- Teachers ---
    teachers = {}
    for i, t in enumerate(raw.get("teachers", [])):
        try:
            unavailable = []
            for slot in t.get("unavailable_slots", []):
                if isinstance(slot, (list, tuple)) and len(slot) == 2:
                    unavailable.append((int(slot[0]), int(slot[1])))
            avoid = []
            for p in t.get("avoid_periods", []):
                avoid.append(int(p))
            teacher = Teacher(
                name=str(t["name"]).strip(),
                subjects=[str(sc).strip() for sc in t["subjects"]],
                unavailable_slots=unavailable,
                max_weekly_load=int(t["max_weekly_load"]),
                avoid_periods=avoid,
            )
            teachers[teacher.name] = teacher
        except (KeyError, ValueError) as e:
            errors.append(f"Teacher #{i+1}: {e}")

    # --- Classes ---
    classes = {}
    for i, c in enumerate(raw.get("classes", [])):
        try:
            cb = ClassBatch(
                name=str(c["name"]).strip(),
                strength=int(c["strength"]),
                subjects=[str(sc).strip() for sc in c["subjects"]],
                lunch_break_slot=int(c["lunch_break_slot"]),
            )
            classes[cb.name] = cb
        except (KeyError, ValueError) as e:
            errors.append(f"Class #{i+1}: {e}")

    # --- Rooms ---
    rooms = {}
    for i, r in enumerate(raw.get("rooms", [])):
        try:
            room = Room(
                name=str(r["name"]).strip(),
                capacity=int(r["capacity"]),
                room_type=str(r["type"]).strip().lower(),
            )
            rooms[room.name] = room
        except (KeyError, ValueError) as e:
            errors.append(f"Room #{i+1}: {e}")

    # --- Time structure ---
    ts_raw = raw.get("time_structure", {})
    try:
        ts = TimeStructure(
            working_days=int(ts_raw.get("working_days", 5)),
            periods_per_day=int(ts_raw.get("periods_per_day", 6)),
            break_periods=[int(p) for p in ts_raw.get("break_periods", [])],
        )
    except (ValueError, TypeError) as e:
        errors.append(f"Time structure: {e}")
        ts = TimeStructure(5, 6)

    if errors:
        raise ValueError("Data loading errors:\n" + "\n".join(f"  - {e}" for e in errors))

    dataset = Dataset(
        subjects=subjects,
        teachers=teachers,
        classes=classes,
        rooms=rooms,
        time_structure=ts,
    )
    dataset.build_subject_teachers()
    logger.info(
        "Loaded dataset: %d subjects, %d teachers, %d classes, %d rooms",
        len(subjects), len(teachers), len(classes), len(rooms),
    )
    return dataset


def load_csv_set(subjects_file, teachers_file, classes_file, rooms_file,
                 working_days: int = 5, periods_per_day: int = 6) -> dict:
    """
    Parse four CSV files (one per entity) into the raw dict format.
    Files can be file paths or file-like objects (Streamlit uploads).
    """
    import pandas as pd

    def read(f):
        if isinstance(f, str):
            return pd.read_csv(f)
        return pd.read_csv(f)

    subj_df = read(subjects_file)
    teach_df = read(teachers_file)
    class_df = read(classes_file)
    room_df = read(rooms_file)

    raw = {"time_structure": {"working_days": working_days,
                               "periods_per_day": periods_per_day,
                               "break_periods": []}}

    # Subjects
    raw["subjects"] = []
    for _, row in subj_df.iterrows():
        raw["subjects"].append({
            "code": str(row["code"]),
            "name": str(row["name"]),
            "weekly_hours": int(row["weekly_hours"]),
            "type": str(row["type"]),
        })

    # Teachers
    raw["teachers"] = []
    for _, row in teach_df.iterrows():
        subjs = str(row["subjects"]).split(";")
        unavail = []
        raw_unavail = row.get("unavailable_slots", "")
        if pd.notna(raw_unavail) and str(raw_unavail).strip():
            for slot in str(raw_unavail).split(";"):
                parts = slot.strip().split(",")
                if len(parts) == 2:
                    unavail.append([int(parts[0]), int(parts[1])])
        avoid = []
        raw_avoid = row.get("avoid_periods", "")
        if pd.notna(raw_avoid) and str(raw_avoid).strip():
            avoid = [int(x) for x in str(raw_avoid).split(";")]
        raw["teachers"].append({
            "name": str(row["name"]),
            "subjects": subjs,
            "unavailable_slots": unavail,
            "max_weekly_load": int(row["max_weekly_load"]),
            "avoid_periods": avoid,
        })

    # Classes
    raw["classes"] = []
    for _, row in class_df.iterrows():
        subjs = str(row["subjects"]).split(";")
        raw["classes"].append({
            "name": str(row["name"]),
            "strength": int(row["strength"]),
            "subjects": subjs,
            "lunch_break_slot": int(row["lunch_break_slot"]),
        })

    # Rooms
    raw["rooms"] = []
    for _, row in room_df.iterrows():
        raw["rooms"].append({
            "name": str(row["name"]),
            "capacity": int(row["capacity"]),
            "type": str(row["type"]),
        })

    return raw


def dataset_to_json(dataset: Dataset) -> dict:
    """Convert a Dataset back to the raw JSON dict for saving."""
    raw = {
        "subjects": [],
        "teachers": [],
        "classes": [],
        "rooms": [],
        "time_structure": {
            "working_days": dataset.time_structure.working_days,
            "periods_per_day": dataset.time_structure.periods_per_day,
            "break_periods": dataset.time_structure.break_periods,
        },
    }
    for s in dataset.subjects.values():
        raw["subjects"].append({
            "code": s.code, "name": s.name,
            "weekly_hours": s.weekly_hours, "type": s.subject_type,
        })
    for t in dataset.teachers.values():
        raw["teachers"].append({
            "name": t.name, "subjects": t.subjects,
            "unavailable_slots": [list(slot) for slot in t.unavailable_slots],
            "max_weekly_load": t.max_weekly_load,
            "avoid_periods": t.avoid_periods,
        })
    for c in dataset.classes.values():
        raw["classes"].append({
            "name": c.name, "strength": c.strength,
            "subjects": c.subjects, "lunch_break_slot": c.lunch_break_slot,
        })
    for r in dataset.rooms.values():
        raw["rooms"].append({
            "name": r.name, "capacity": r.capacity, "type": r.room_type,
        })
    return raw
