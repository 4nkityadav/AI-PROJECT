"""
app.py — Class Pilot: AI-Based Timetable Scheduler.
Modern SaaS Web Application for College Timetable Management.

4-Stage Guided Workflow:
  Stage 1: Load Data
  Stage 2: Generate Timetable
  Stage 3: View Timetable
  Stage 4: Manage & Analyze (2x2 Workspace Grid: Edit, Compare, Benchmark, Export)
"""

import streamlit as st
import pandas as pd
import json
import random
import time
import logging
import os
import sys

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.models import (
    Dataset, Timetable, Session, SolverConfig, Result, ViolationReport,
)
from core.loader import load_json, parse_dataset, dataset_to_json, load_csv_set
from core.validator import validate_dataset
from core.teacher_assign import assign_teachers_and_create_sessions
from core.constraints import count_violations, compute_cost
from core.backtracking import solve_backtracking
from core.min_conflicts import solve_min_conflicts
from core.annealing import solve_simulated_annealing
from core.hybrid import solve_hybrid
from core.hill_climbing import solve_hill_climbing
from core.exporters import (
    timetable_to_grid_df, master_timetable_grid_df, export_csv, export_excel, export_pdf,
)
from core.experiments import run_experiments, SOLVERS
from ui.styles import (
    inject_css, render_header,
    render_timetable_html, render_master_timetable_html, get_subject_color,
)

logging.basicConfig(level=logging.INFO)

# Sample & custom datasets
from data.generate_datasets import (
    get_small_dataset, get_medium_dataset, get_large_dataset, generate_custom_dataset,
)


def main():
    st.set_page_config(
        page_title="Class Pilot — AI-Based Timetable Scheduler",
        page_icon="ui/favicon.png",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_css()

    # ── Session state defaults ──
    defaults = {
        "raw_data": None,
        "dataset": None,
        "result": None,
        "timetable": None,
        "report": None,
        "config": SolverConfig(),
        "edit_history": [],      # For undo/redo
        "edit_redo": [],
        "compare_results": None,
        "experiment_results": None,
        "current_stage": 1,      # 1: Load Data, 2: Generate, 3: View, 4: Manage & Analyze
        "stage4_tool": None,     # None (2x2 grid), 'edit', 'compare', 'benchmark', 'export'
        "dataset_name": "None",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # ── Clean Top Header (Class Pilot Branding & Status) ──
    render_header(
        dataset=st.session_state.dataset,
        timetable=st.session_state.timetable,
        report=st.session_state.report,
    )

    # ── Interactive Horizontal Stepper Bar ──
    has_data = st.session_state.dataset is not None
    has_timetable = st.session_state.timetable is not None
    stage = st.session_state.current_stage

    lbl_1 = "✓ 1. Load Data" if (has_data and stage != 1) else ("▶ 1. Load Data" if stage == 1 else "1. Load Data")
    lbl_2 = "✓ 2. Generate Timetable" if (has_timetable and stage != 2) else ("▶ 2. Generate Timetable" if stage == 2 else "2. Generate Timetable")
    lbl_3 = "✓ 3. View Timetable" if (has_timetable and stage != 3) else ("▶ 3. View Timetable" if stage == 3 else "3. View Timetable")
    lbl_4 = "▶ 4. Manage & Analyze" if stage == 4 else "4. Manage & Analyze"

    s_c1, s_c2, s_c3, s_c4 = st.columns(4)
    with s_c1:
        if st.button(lbl_1, type="primary" if stage == 1 else "secondary", use_container_width=True, key="nav_s1"):
            st.session_state.current_stage = 1
            st.session_state.stage4_tool = None
            st.rerun()
    with s_c2:
        if st.button(lbl_2, type="primary" if stage == 2 else "secondary", disabled=not has_data, use_container_width=True, key="nav_s2"):
            st.session_state.current_stage = 2
            st.session_state.stage4_tool = None
            st.rerun()
    with s_c3:
        if st.button(lbl_3, type="primary" if stage == 3 else "secondary", disabled=not has_timetable, use_container_width=True, key="nav_s3"):
            st.session_state.current_stage = 3
            st.session_state.stage4_tool = None
            st.rerun()
    with s_c4:
        if st.button(lbl_4, type="primary" if stage == 4 else "secondary", disabled=not has_timetable, use_container_width=True, key="nav_s4"):
            st.session_state.current_stage = 4
            st.session_state.stage4_tool = None
            st.rerun()

    # ── Route to Current Stage ──
    if st.session_state.current_stage == 1:
        stage_1_load_data()
    elif st.session_state.current_stage == 2:
        stage_2_generate()
    elif st.session_state.current_stage == 3:
        stage_3_view()
    elif st.session_state.current_stage == 4:
        stage_4_manage_and_analyze()


# ════════════════════════════════════════════
# STAGE 1: LOAD DATA
# ════════════════════════════════════════════

def stage_1_load_data():
    st.markdown("### Stage 1: Load Academic Data")
    st.caption("Import course curriculum, faculty rosters, student batches, and room facilities.")

    tab_demo, tab_upload, tab_custom = st.tabs([
        "Demo Datasets", "Upload JSON / CSV Files", "Synthetic Dataset Generator"
    ])

    # ── Section A: Demo Data ──
    with tab_demo:
        with st.container(border=True):
            st.markdown("#### Select Pre-configured Demo Dataset")
            st.caption("Load a fully verified college department model with a single click.")
            d_col1, d_col2 = st.columns([1, 1])

            with d_col1:
                demo_choice = st.selectbox(
                    "Select Academic Benchmark",
                    [
                        "Standard Demo — Medium (5 Classes, 12 Teachers, 8 Rooms, 5x6)",
                        "Fast Verification — Small (3 Classes, 6 Teachers, 4 Rooms, 5x6)",
                        "Enterprise Scale — Large (8 Classes, 15 Teachers, 8 Rooms, 5x7)",
                    ],
                    key="demo_choice",
                )
                if st.button("Load Selected Dataset", type="primary", key="btn_load_demo"):
                    if "Small" in demo_choice:
                        st.session_state.raw_data = get_small_dataset()
                        st.session_state.dataset_name = "Small Demo (3 Classes)"
                    elif "Large" in demo_choice:
                        st.session_state.raw_data = get_large_dataset()
                        st.session_state.dataset_name = "Large Demo (8 Classes)"
                    else:
                        st.session_state.raw_data = get_medium_dataset()
                        st.session_state.dataset_name = "Medium Demo (5 Classes)"
                    _parse_and_validate()
                    st.rerun()

            with d_col2:
                st.markdown("**Dataset Details:**")
                if "Small" in demo_choice:
                    st.markdown("- **Cohorts:** 3 Batches (CSE-1, CSE-2, ECE-1)\n- **Faculty:** 6 Professors (with leaves)\n- **Facilities:** 4 Rooms (Classrooms + Labs)\n- **Volume:** ~35 Teaching Sessions")
                elif "Large" in demo_choice:
                    st.markdown("- **Cohorts:** 8 Batches (Engineering Department)\n- **Faculty:** 15 Professors (with complex constraints)\n- **Facilities:** 8 Rooms (Halls + Labs)\n- **Volume:** ~92 Teaching Sessions")
                else:
                    st.markdown("- **Cohorts:** 5 Batches (CSE-3A, CSE-3B, IT-3A, AI-DS-2A, ECE-2A)\n- **Faculty:** 12 Professors (with leaves & workload caps)\n- **Facilities:** 8 Rooms (Lecture Halls + Dedicated Labs)\n- **Volume:** ~62 Teaching Sessions")


    # ── Section B: Upload Data ──
    with tab_upload:
        with st.container(border=True):
            st.markdown("#### Upload Custom College Data")
            up_mode = st.radio("Upload Format", ["Consolidated JSON File", "Separate Relational CSVs"], horizontal=True, key="up_mode")

            if "JSON" in up_mode:
                json_file = st.file_uploader("Upload Department JSON File", type=["json"], key="json_file")
                if json_file and st.button("Load Uploaded JSON", key="btn_load_json"):
                    try:
                        st.session_state.raw_data = json.load(json_file)
                        st.session_state.dataset_name = json_file.name
                        _parse_and_validate()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error reading JSON: {e}")
            else:
                c1, c2 = st.columns(2)
                with c1:
                    f_subj = st.file_uploader("Subjects (CSV)", type=["csv"], key="csv_subj")
                    f_teach = st.file_uploader("Teachers (CSV)", type=["csv"], key="csv_teach")
                with c2:
                    f_cls = st.file_uploader("Classes (CSV)", type=["csv"], key="csv_cls")
                    f_room = st.file_uploader("Rooms (CSV)", type=["csv"], key="csv_room")

                if all([f_subj, f_teach, f_cls, f_room]) and st.button("Load CSV Dataset Set", key="btn_load_csv"):
                    try:
                        st.session_state.raw_data = load_csv_set(f_subj, f_teach, f_cls, f_room)
                        st.session_state.dataset_name = "Uploaded CSV Dataset"
                        _parse_and_validate()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error reading CSV files: {e}")

            template = {
                "subjects": [{"code": "CS101", "name": "Programming Fundamentals", "weekly_hours": 3, "type": "theory"}],
                "teachers": [{"name": "Dr. Sharma", "subjects": ["CS101"], "unavailable_slots": [], "max_weekly_load": 18, "avoid_periods": []}],
                "classes": [{"name": "CSE-A", "strength": 40, "subjects": ["CS101"], "lunch_break_slot": 2}],
                "rooms": [{"name": "Room-1", "capacity": 50, "type": "classroom"}],
                "time_structure": {"working_days": 5, "periods_per_day": 6, "break_periods": []},
            }
            st.download_button(
                "Download Sample JSON Template",
                json.dumps(template, indent=2),
                "class_pilot_template.json",
                "application/json",
            )

    # ── Section C: Synthetic Generator ──
    with tab_custom:
        with st.container(border=True):
            st.markdown("#### Synthetic Department Generator")
            st.caption("Generate a solvable, fully balanced academic department model.")
            g_c1, g_c2, g_c3 = st.columns(3)
            with g_c1:
                gen_classes = st.slider("Number of Classes / Batches", 2, 10, 4, key="gen_cls")
                gen_teachers = st.slider("Number of Teachers", 4, 20, 8, key="gen_teach")
            with g_c2:
                gen_rooms = st.slider("Classrooms & Labs", 3, 12, 6, key="gen_room")
                gen_days = st.slider("Working Days / Week", 4, 6, 5, key="gen_days")
            with g_c3:
                gen_periods = st.slider("Periods / Day", 5, 8, 6, key="gen_per")
                st.write("")
                if st.button("Generate & Load Synthetic Model", type="primary", key="btn_gen_synth"):
                    st.session_state.raw_data = generate_custom_dataset(
                        num_classes=gen_classes,
                        num_teachers=gen_teachers,
                        num_rooms=gen_rooms,
                        days=gen_days,
                        periods_per_day=gen_periods,
                    )
                    st.session_state.dataset_name = f"Synthetic Model ({gen_classes} Classes, {gen_teachers} Faculty)"
                    _parse_and_validate()
                    st.rerun()

    # ── Section D: Data Summary & Validation Display ──
    if st.session_state.dataset:
        dataset = st.session_state.dataset
        with st.container(border=True):
            st.markdown("#### Department Summary & Roster")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Student Classes", f"{len(dataset.classes)}")
            m2.metric("Subjects & Courses", f"{len(dataset.subjects)}")
            m3.metric("Faculty Members", f"{len(dataset.teachers)}")
            m4.metric("Rooms & Facilities", f"{len(dataset.rooms)}")

            tab_s, tab_t, tab_c, tab_r = st.tabs(["Subjects", "Faculty Roster", "Classes", "Rooms"])
            with tab_s:
                st.dataframe(pd.DataFrame([
                    {"Code": s.code, "Course Name": s.name, "Hours/Week": s.weekly_hours, "Type": s.subject_type.upper()}
                    for s in dataset.subjects.values()
                ]), hide_index=True, use_container_width=True)
            with tab_t:
                st.dataframe(pd.DataFrame([
                    {
                        "Teacher Name": t.name,
                        "Assigned Subjects": ", ".join(t.subjects),
                        "Max Weekly Load": f"{t.max_weekly_load} hrs",
                        "Unavailable Slots": f"{len(t.unavailable_slots)} slot(s)" if t.unavailable_slots else "Available all week",
                    }
                    for t in dataset.teachers.values()
                ]), hide_index=True, use_container_width=True)
            with tab_c:
                st.dataframe(pd.DataFrame([
                    {"Class Batch": c.name, "Strength": f"{c.strength} students", "Curriculum": ", ".join(c.subjects), "Lunch Period": f"Period {c.lunch_break_slot + 1}"}
                    for c in dataset.classes.values()
                ]), hide_index=True, use_container_width=True)
            with tab_r:
                st.dataframe(pd.DataFrame([
                    {"Room Name": r.name, "Capacity": f"{r.capacity} seats", "Room Type": r.room_type.upper()}
                    for r in dataset.rooms.values()
                ]), hide_index=True, use_container_width=True)

    # ── Bottom Navigation ──
    b_col1, b_col2 = st.columns([3, 1])
    with b_col2:
        if st.button("Next: Generate Timetable →", type="primary", disabled=(st.session_state.dataset is None), use_container_width=True, key="btn_next_s2"):
            st.session_state.current_stage = 2
            st.rerun()


def _parse_and_validate():
    """Parse raw data and run validation."""
    try:
        dataset = parse_dataset(st.session_state.raw_data)
        errors, warnings = validate_dataset(dataset)

        if errors:
            st.error("Validation failed with errors:")
            for e in errors:
                st.error(f"Error: {e}")
            return

        config = st.session_state.config
        assign_teachers_and_create_sessions(dataset, config)
        st.session_state.dataset = dataset
        # Clear previous timetable results on new dataset load
        st.session_state.result = None
        st.session_state.timetable = None
        st.session_state.report = None

        if warnings:
            for w in warnings:
                st.warning(f"Warning: {w}")

        st.success("Data Loaded Successfully: All required entities and syllabus hours verified.")

    except Exception as e:
        st.error(f"Error parsing data: {e}")


# ════════════════════════════════════════════
# STAGE 2: GENERATE TIMETABLE
# ════════════════════════════════════════════

def stage_2_generate():
    st.markdown("### Stage 2: Generate Timetable")
    st.caption("Configure optimization algorithms, computation budgets, and penalty weights.")

    if not st.session_state.dataset:
        st.info("Please load data in Stage 1 first.")
        if st.button("← Go to Stage 1: Load Data", key="btn_goto_s1"):
            st.session_state.current_stage = 1
            st.rerun()
        return

    dataset = st.session_state.dataset

    # ── Section A: Configuration Section ──
    # Top Row: Select Algorithm and Computation Budget side by side in the same horizontal row on desktop
    cfg_col1, cfg_col2 = st.columns([1, 1])

    with cfg_col1:
        with st.container(border=True):
            st.markdown("#### Select Algorithm")
            algo = st.selectbox(
                "Optimization Algorithm",
                [
                    "Backtracking (Heuristics)",
                    "Min-Conflicts",
                    "Hybrid (BT + SA)",
                    "Simulated Annealing",
                    "Hill Climbing",
                    "Backtracking (Plain)",
                ],
                key="algo_select",
            )

            if algo == "Backtracking (Heuristics)":
                st.caption("MRV + Degree Heuristic + Forward Checking. Guaranteed conflict-free.")
            elif algo == "Min-Conflicts":
                st.caption("Fast local search with FastOccupancy conflict matrix. Millisecond solver.")
            elif algo == "Hybrid (BT + SA)":
                st.caption("Backtracking creates guaranteed valid schedule, then SA refines comfort.")
            elif algo == "Simulated Annealing":
                st.caption("Probabilistic local search exploring assignment space.")
            elif algo == "Hill Climbing":
                st.caption("Steepest-ascent search with random restart recovery.")
            else:
                st.caption("Systematic unguided search baseline without heuristics.")

            if "Heuristics" in algo:
                st.markdown("**Active Heuristics:**")
                h_c1, h_c2 = st.columns(2)
                with h_c1:
                    use_mrv = st.checkbox("MRV (Min Remaining Values)", value=True, key="h_mrv")
                    use_degree = st.checkbox("Degree Heuristic", value=True, key="h_deg")
                    use_fc = st.checkbox("Forward Checking", value=True, key="h_fc")
                with h_c2:
                    use_lcv = st.checkbox("LCV (Least Constraining)", value=False, key="h_lcv")
                    use_ac3 = st.checkbox("AC-3 Preprocessing", value=False, key="h_ac3")
            else:
                use_mrv = "Heuristics" in algo
                use_degree = use_mrv
                use_fc = use_mrv
                use_lcv = False
                use_ac3 = False

    with cfg_col2:
        with st.container(border=True):
            st.markdown("#### Computation Budget")
            p_c1, p_c2 = st.columns(2)
            with p_c1:
                seed = st.number_input("Deterministic Seed", value=42, step=1, key="param_seed")
                time_limit = st.number_input("Time Limit (seconds)", value=30.0, step=5.0, key="param_time")
            with p_c2:
                max_nodes = st.number_input("Max Nodes / Steps", value=100000, step=10000, key="param_nodes")

            if "Min-Conflicts" in algo:
                walk_prob = st.slider("Random Walk Probability", 0.0, 0.2, 0.02, key="param_walk")
                restart_n = st.number_input("Restart After N No-Improve", value=1500, key="param_restart")
            else:
                walk_prob = 0.02
                restart_n = 1500

            if "Annealing" in algo or "Hybrid" in algo:
                sa_temp = st.number_input("SA Initial Temperature", value=80.0, key="param_temp")
                sa_alpha = st.slider("Cooling Rate (Alpha)", 0.9, 0.999, 0.99, key="param_alpha")
            else:
                sa_temp = 80.0
                sa_alpha = 0.99

    # Directly below top row: Timetable Type and Soft Constraint Penalty Weights
    with st.container(border=True):
        st.markdown("#### Timetable Type")
        preset = st.selectbox(
            "Select Objective Profile",
            ["Standard Balanced", "Student Welfare (Min Gaps)", "Faculty Workload Balancing", "Custom Weights"],
            key="preset",
        )
        if preset == "Student Welfare (Min Gaps)":
            def_w1, def_w2, def_w3, def_w4, def_w5 = 4.0, 3.0, 3.0, 1.0, 1.0
        elif preset == "Faculty Workload Balancing":
            def_w1, def_w2, def_w3, def_w4, def_w5 = 1.0, 1.0, 2.0, 4.0, 4.0
        elif preset == "Standard Balanced":
            def_w1, def_w2, def_w3, def_w4, def_w5 = 2.0, 2.0, 2.0, 2.0, 2.0
        else:
            def_w1, def_w2, def_w3, def_w4, def_w5 = 2.0, 2.0, 3.0, 1.0, 2.0

        st.markdown("##### Soft Constraint Penalty Weights")
        st.caption("Adjust penalty multipliers applied to soft objective violations during schedule scoring.")
        w_c1, w_c2 = st.columns(2)
        with w_c1:
            w1 = st.slider("S1: Avoid student idle gap hours", 0.0, 5.0, def_w1, key="w_s1", help="Penalizes empty periods between classes in a student's daily schedule.")
            w2 = st.slider("S2: Avoid duplicate subject on same day", 0.0, 5.0, def_w2, key="w_s2", help="Penalizes scheduling multiple lectures of the same subject on the same day.")
            w3 = st.slider("S3: Enforce continuous laboratory blocks", 0.0, 5.0, def_w3, key="w_s3", help="Ensures multi-period lab sessions remain contiguous.")
        with w_c2:
            w4 = st.slider("S4: Accommodate faculty preferred slots", 0.0, 5.0, def_w4, key="w_s4", help="Honors faculty time preferences wherever possible.")
            w5 = st.slider("S5: Avoid 3+ consecutive faculty periods", 0.0, 5.0, def_w5, key="w_s5", help="Prevents teacher fatigue by capping consecutive teaching hours.")

    # Save solver configuration
    config = SolverConfig(
        seed=int(seed), time_limit=time_limit, max_nodes=int(max_nodes),
        max_iterations=int(max_nodes),
        use_mrv=use_mrv, use_degree=use_degree, use_lcv=use_lcv,
        use_forward_checking=use_fc, use_ac3=use_ac3,
        random_walk_prob=walk_prob, restart_after=int(restart_n),
        sa_initial_temp=sa_temp, sa_cooling_alpha=sa_alpha,
        weight_s1=w1, weight_s2=w2, weight_s3=w3, weight_s4=w4, weight_s5=w5,
    )
    st.session_state.config = config

    # ── Section B: Generate Button ──
    if st.button("Generate Timetable", type="primary", use_container_width=True, key="btn_generate"):
        _run_solver(algo, dataset, config)

    # ── Section C: Optimization Execution Summary ──
    if st.session_state.result:
        result = st.session_state.result
        report = st.session_state.report

        with st.container(border=True):
            st.markdown("#### Optimization Execution Summary")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Selected Algorithm", result.algorithm[:22])
            c2.metric("Execution Time", f"{result.time_seconds:.3f}s")
            c3.metric("Nodes / Steps", f"{result.nodes_or_iterations:,}" if result.nodes_or_iterations > 0 else "N/A")
            c4.metric("Hard Violations", result.hard_violations if result.hard_violations >= 0 else "0")
            c5.metric("Soft Penalty", f"{result.soft_penalty:.1f}" if result.soft_penalty >= 0 else "0.0")

            if result.success:
                st.success("Conflict-Free Schedule Generated: All hard constraints satisfied (0 conflicts).")
            elif result.status == "timeout":
                st.warning("Time Limit Elapsed: Presenting best partial schedule identified.")
            else:
                st.error(f"Conflicts Present: Solver finished with {result.hard_violations} unresolved conflicts.")

        # ── Section D: Statutory Constraint Compliance Breakdown ──
        if report:
            with st.container(border=True):
                st.markdown("#### Statutory Constraint Compliance Breakdown")

                hard_labels = {
                    "H1": "Teacher Clash Prevention (No faculty double-booking)",
                    "H2": "Class Clash Prevention (No cohort double-booking)",
                    "H3": "Room Clash Prevention (No room double-booking)",
                    "H4": "Room Capacity Compliance (Cohort strength <= Room capacity)",
                    "H5": "Room Type Match (Labs in laboratories, theory in classrooms)",
                    "H6": "Teacher Availability (No teaching during leaves/blocked slots)",
                    "H7": "Required Weekly Subject Hours (Complete syllabus contact hours)",
                    "H8": "Teacher Workload Limits (Weekly maximum teaching hours cap)",
                    "H9": "Class Lunch Breaks (Designated lunch break preserved)",
                }

                hard_rows = []
                for code in ["H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8", "H9"]:
                    count = report.per_code.get(code, 0)
                    hard_rows.append({
                        "Code": code,
                        "Constraint Name": hard_labels[code],
                        "Violations": count,
                        "Status": "Passed (0 conflicts)" if count == 0 else f"Failed ({count} conflicts)",
                    })
                st.dataframe(pd.DataFrame(hard_rows), hide_index=True, use_container_width=True)

                if report.hard_violations:
                    st.markdown("**Violated Incident Log:**")
                    for v in report.hard_violations:
                        st.error(f"{v.code}: {v.message}")

                st.markdown("##### Soft Objectives Compliance")
                soft_labels = {
                    "S1": "Avoid Student Idle Gaps",
                    "S2": "Avoid Duplicate Subjects on Same Day",
                    "S3": "Keep Lab Blocks Strictly Consecutive",
                    "S4": "Honor Faculty Preferred Teaching Slots",
                    "S5": "Avoid 3+ Consecutive Faculty Periods",
                }
                soft_rows = []
                for code in ["S1", "S2", "S3", "S4", "S5"]:
                    count = report.per_code.get(code, 0)
                    soft_rows.append({
                        "Code": code,
                        "Objective": soft_labels[code],
                        "Occurrences": count,
                        "Status": "Optimal" if count == 0 else f"{count} non-optimal occurrence(s)",
                    })
                st.dataframe(pd.DataFrame(soft_rows), hide_index=True, use_container_width=True)

        # ── Section E: Timetable Instant Preview ──
        if st.session_state.timetable:
            with st.container(border=True):
                st.markdown("#### Timetable Instant Preview")
                classes = list(dataset.classes.keys())
                prev_c1, prev_c2 = st.columns([1, 3])
                with prev_c1:
                    prev_cls = st.selectbox("Select Class to Preview", classes, key="prev_cls")
                with prev_c2:
                    st.caption(f"Previewing schedule for **{prev_cls}**. Advance to Stage 3 for Teacher, Room, and Master grid views.")
                html = render_timetable_html(st.session_state.timetable, dataset, "class", prev_cls)
                st.markdown(html, unsafe_allow_html=True)

    # ── Bottom Navigation ──
    b_col1, b_col2 = st.columns([1, 1])
    with b_col1:
        if st.button("← Back: Load Data", use_container_width=True, key="btn_back_s1"):
            st.session_state.current_stage = 1
            st.rerun()
    with b_col2:
        if st.button("Next: View Timetable →", type="primary", disabled=(st.session_state.timetable is None), use_container_width=True, key="btn_next_s3"):
            st.session_state.current_stage = 3
            st.rerun()


def _run_solver(algo: str, dataset: Dataset, config: SolverConfig):
    """Run optimization solver."""
    random.seed(config.seed)

    with st.spinner(f"Running {algo} optimization solver..."):
        if algo == "Backtracking (Plain)":
            cfg = SolverConfig(
                seed=config.seed, time_limit=config.time_limit, max_nodes=config.max_nodes,
                use_mrv=False, use_degree=False, use_lcv=False,
                use_forward_checking=False, use_ac3=False,
                lab_block_size=config.lab_block_size, lab_mode=config.lab_mode,
                weight_s1=config.weight_s1, weight_s2=config.weight_s2,
                weight_s3=config.weight_s3, weight_s4=config.weight_s4,
                weight_s5=config.weight_s5,
            )
            result = solve_backtracking(dataset, cfg)
        elif "Heuristics" in algo:
            result = solve_backtracking(dataset, config)
        elif algo == "Min-Conflicts":
            result = solve_min_conflicts(dataset, config)
        elif algo == "Simulated Annealing":
            result = solve_simulated_annealing(dataset, config)
        elif "Hybrid" in algo:
            result = solve_hybrid(dataset, config)
        elif algo == "Hill Climbing":
            result = solve_hill_climbing(dataset, config)
        else:
            st.error(f"Unrecognized algorithm: {algo}")
            return

    st.session_state.result = result
    if result.timetable:
        st.session_state.timetable = result.timetable
        st.session_state.report = count_violations(result.timetable, dataset, config)
        st.session_state.edit_history = []
        st.session_state.edit_redo = []


# ════════════════════════════════════════════
# STAGE 3: VIEW TIMETABLE
# ════════════════════════════════════════════

def stage_3_view():
    st.markdown("### Stage 3: View Timetable")
    st.caption("Inspect schedules by class, teacher, room, or full master grid.")

    if not st.session_state.timetable or not st.session_state.dataset:
        st.info("Generate a timetable in Stage 2 first.")
        if st.button("← Go to Stage 2: Generate Timetable", key="btn_goto_s2"):
            st.session_state.current_stage = 2
            st.rerun()
        return

    timetable = st.session_state.timetable
    dataset = st.session_state.dataset

    # Highlight filter
    with st.container(border=True):
        hl_col1, hl_col2 = st.columns([3, 1])
        with hl_col1:
            highlight = st.text_input("Highlight Course, Teacher, Room, or Class:", placeholder="e.g. CS101, Sharma, Room-1...", key="v_highlight")
        with hl_col2:
            st.write("")
            st.caption("Matches illuminate with high-contrast borders.")

    tab_class, tab_teacher, tab_room, tab_master = st.tabs([
        "By Class / Batch", "By Teacher", "By Room", "Master Schedule"
    ])

    with tab_class:
        with st.container(border=True):
            cls_name = st.selectbox("Select Class / Batch", list(dataset.classes.keys()), key="v_cls")
            html = render_timetable_html(timetable, dataset, "class", cls_name, highlight_text=highlight)
            st.markdown(html, unsafe_allow_html=True)

    with tab_teacher:
        with st.container(border=True):
            t_name = st.selectbox("Select Teacher", list(dataset.teachers.keys()), key="v_teach")
            # Calculate free periods
            ts = dataset.time_structure
            total_slots = ts.working_days * ts.periods_per_day
            occupied = 0
            for session, val in timetable.assignment.items():
                if val and session.teacher_name == t_name:
                    occupied += session.block_size
            free_slots = total_slots - occupied

            t_m1, t_m2, t_m3 = st.columns(3)
            t_m1.metric("Teaching Load", f"{occupied} hrs/week")
            t_m2.metric("Contractual Cap", f"{dataset.teachers[t_name].max_weekly_load} hrs")
            t_m3.metric("Free Periods", f"{free_slots} slots")

            html = render_timetable_html(timetable, dataset, "teacher", t_name, highlight_text=highlight)
            st.markdown(html, unsafe_allow_html=True)

    with tab_room:
        with st.container(border=True):
            r_name = st.selectbox("Select Room", list(dataset.rooms.keys()), key="v_room")
            room_obj = dataset.rooms[r_name]
            ts = dataset.time_structure
            total_slots = ts.working_days * ts.periods_per_day
            used_slots = 0
            for session, val in timetable.assignment.items():
                if val and val[2] == r_name:
                    used_slots += session.block_size
            util = (used_slots / total_slots * 100) if total_slots > 0 else 0

            r_m1, r_m2, r_m3 = st.columns(3)
            r_m1.metric("Facility Type", room_obj.room_type.upper())
            r_m2.metric("Seating Capacity", f"{room_obj.capacity} seats")
            r_m3.metric("Room Utilization", f"{util:.0f}% ({used_slots}/{total_slots} slots)")

            html = render_timetable_html(timetable, dataset, "room", r_name, highlight_text=highlight)
            st.markdown(html, unsafe_allow_html=True)

    with tab_master:
        with st.container(border=True):
            m_mode = st.radio("Group Columns By", ["Classes / Student Batches", "Rooms & Labs"], horizontal=True, key="v_master_group")
            group_by = "class" if "Classes" in m_mode else "room"
            master_html = render_master_timetable_html(timetable, dataset, group_by=group_by, highlight_text=highlight)
            st.markdown(master_html, unsafe_allow_html=True)

    # ── Bottom Navigation ──
    b_col1, b_col2 = st.columns([1, 1])
    with b_col1:
        if st.button("← Back: Generate Timetable", use_container_width=True, key="btn_back_s2"):
            st.session_state.current_stage = 2
            st.rerun()
    with b_col2:
        if st.button("Next: Manage & Analyze →", type="primary", use_container_width=True, key="btn_next_s4"):
            st.session_state.current_stage = 4
            st.session_state.stage4_tool = None
            st.rerun()


# ════════════════════════════════════════════
# STAGE 4: MANAGE & ANALYZE
# ════════════════════════════════════════════

def stage_4_manage_and_analyze():
    tool = st.session_state.get("stage4_tool")

    if tool == "edit":
        render_tool_edit()
    elif tool == "compare":
        render_tool_compare()
    elif tool == "benchmark":
        render_tool_benchmark()
    elif tool == "export":
        render_tool_export()
    else:
        render_stage4_workspace()


def render_stage4_workspace():
    """Display the 2x2 desktop grid for Stage 4."""
    st.markdown("### Stage 4: Manage & Analyze Timetable")
    st.caption("Central workspace for schedule editing, algorithm benchmarking, empirical studies, and multi-format exports.")

    if not st.session_state.timetable or not st.session_state.dataset:
        st.info("Generate a timetable in Stage 2 first.")
        if st.button("← Go to Stage 2: Generate Timetable", key="btn_goto_s2_m"):
            st.session_state.current_stage = 2
            st.rerun()
        return

    # ── 2x2 Desktop Grid ──
    row1_c1, row1_c2 = st.columns(2)

    with row1_c1:
        with st.container(border=True):
            st.markdown("#### Edit Timetable")
            st.caption("Manually adjust scheduled sessions, reassign rooms, or move time slots with instant live clash detection.")
            st.write("")
            if st.button("Open Timetable Editor →", type="primary", use_container_width=True, key="btn_open_edit"):
                st.session_state.stage4_tool = "edit"
                st.rerun()

    with row1_c2:
        with st.container(border=True):
            st.markdown("#### Compare Algorithms")
            st.caption("Benchmark multiple algorithms on runtime, nodes expanded, hard violations, and soft penalty scores.")
            st.write("")
            if st.button("Open Algorithm Comparison →", type="primary", use_container_width=True, key="btn_open_compare"):
                st.session_state.stage4_tool = "compare"
                st.rerun()

    row2_c1, row2_c2 = st.columns(2)

    with row2_c1:
        with st.container(border=True):
            st.markdown("#### Empirical Benchmark")
            st.caption("Run 10-trial randomized experiments, scalability comparisons on small and large datasets, and heuristic ablation studies.")
            st.write("")
            if st.button("Open Empirical Benchmark →", type="primary", use_container_width=True, key="btn_open_benchmark"):
                st.session_state.stage4_tool = "benchmark"
                st.rerun()

    with row2_c2:
        with st.container(border=True):
            st.markdown("#### Download & Export")
            st.caption("Export certified timetables in multi-sheet Excel (.xlsx), PDF documents, CSV database records, or JSON system archives.")
            st.write("")
            if st.button("Open Download & Export →", type="primary", use_container_width=True, key="btn_open_export"):
                st.session_state.stage4_tool = "export"
                st.rerun()

    # Bottom Navigation
    if st.button("← Back: View Timetable", key="btn_back_s3"):
        st.session_state.current_stage = 3
        st.rerun()


# ── Sub-Tool 1: Edit Timetable ──

def render_tool_edit():
    """GRID 1: Edit Timetable with live constraint validation and clash identification."""
    if st.button("← Back to Manage & Analyze Workspace", key="btn_back_ws_edit"):
        st.session_state.stage4_tool = None
        st.rerun()

    st.markdown("### Edit Timetable")
    st.caption("Interactive manual schedule editing with live clash detection and conflict resolution.")

    timetable = st.session_state.timetable
    dataset = st.session_state.dataset
    config = st.session_state.config
    ts = dataset.time_structure

    # 1. Ask user to select class / batch first
    with st.container(border=True):
        st.markdown("#### Step 1: Select Student Class / Batch")
        classes = list(dataset.classes.keys())
        active_cls = st.selectbox("Select Class to Edit", classes, key="edit_cls_picker")

    # 2. Display that class's timetable
    with st.container(border=True):
        st.markdown(f"#### Current Schedule for {active_cls}")
        html = render_timetable_html(timetable, dataset, "class", active_cls)
        st.markdown(html, unsafe_allow_html=True)

    # 3. Filter sessions belonging to this class
    class_sessions = [s for s in timetable.assignment.keys() if s.class_name == active_cls]
    if not class_sessions:
        st.warning("No sessions found for this class.")
        return

    # Session selection
    with st.container(border=True):
        st.markdown("#### Step 2: Select Session & Target Reassignment")
        e_col1, e_col2 = st.columns(2)

        with e_col1:
            sess_labels = [f"{s.subject_code} — {s.teacher_name} ({'LAB' if dataset.subjects.get(s.subject_code, None) and dataset.subjects[s.subject_code].subject_type == 'lab' else 'THEORY'}) [Block: {s.block_size}h]" for s in class_sessions]
            sel_s_idx = st.selectbox("Select Scheduled Session", range(len(class_sessions)), format_func=lambda i: sess_labels[i], key="e_sess_sel")
            selected_session = class_sessions[sel_s_idx]

            curr_val = timetable.assignment.get(selected_session)
            if curr_val:
                c_d, c_p, c_r = curr_val
                st.info(f"Current Allocation: {ts.day_names[c_d]}, Period {c_p+1}, Room: {c_r}")

        with e_col2:
            st.markdown("**Target Allocation:**")
            t_c1, t_c2, t_c3 = st.columns(3)
            with t_c1:
                new_day = st.selectbox("New Day", range(ts.working_days), format_func=lambda d: ts.day_names[d], key="edit_new_day")
            with t_c2:
                new_period = st.selectbox("New Period", range(ts.periods_per_day), format_func=lambda p: f"P{p+1}", key="edit_new_period")
            with t_c3:
                new_room = st.selectbox("New Room", list(dataset.rooms.keys()), key="edit_new_room")

    # 4. Action bar with Live Constraint Validation
    with st.container(border=True):
        st.markdown("#### Step 3: Verify & Commit Changes")
        act_c1, act_c2, act_c3, act_c4 = st.columns(4)
        with act_c1:
            btn_prev = st.button("Preview Changes", use_container_width=True, key="btn_edit_preview")
        with act_c2:
            btn_commit = st.button("Save New Timetable", type="primary", use_container_width=True, key="btn_edit_commit")
        with act_c3:
            btn_undo = st.button("Undo / Revert", disabled=not st.session_state.edit_history, use_container_width=True, key="btn_edit_undo")
        with act_c4:
            btn_sugg = st.button("Suggest Feasible Slots", use_container_width=True, key="btn_edit_suggest")

    # Preview logic
    if btn_prev:
        temp_assign = dict(timetable.assignment)
        temp_assign[selected_session] = (new_day, new_period, new_room)
        temp_tt = Timetable(assignment=temp_assign)
        new_rep = count_violations(temp_tt, dataset, config)

        if new_rep.hard_violations:
            st.error(f"Invalid Move: This change creates {new_rep.hard_count} hard violation(s).")
            for v in new_rep.hard_violations:
                st.markdown(f"- **{v.code}:** {v.message}")
        else:
            st.success(f"Valid Move: 0 conflicts detected. Safe to apply. Soft penalty: {new_rep.soft_penalty:.1f}")

    # Save logic
    if btn_commit:
        temp_assign = dict(timetable.assignment)
        temp_assign[selected_session] = (new_day, new_period, new_room)
        temp_tt = Timetable(assignment=temp_assign)
        new_rep = count_violations(temp_tt, dataset, config)

        if new_rep.hard_violations:
            st.error(f"Cannot save invalid timetable. It introduces {new_rep.hard_count} conflicts.")
            for v in new_rep.hard_violations:
                st.markdown(f"- **{v.code}:** {v.message}")
        else:
            st.session_state.edit_history.append((selected_session, timetable.assignment.get(selected_session)))
            st.session_state.edit_redo.clear()
            timetable.assignment[selected_session] = (new_day, new_period, new_room)
            st.session_state.report = new_rep
            st.success("Timetable updated successfully!")
            st.rerun()

    # Undo logic
    if btn_undo:
        sess_u, old_val = st.session_state.edit_history.pop()
        st.session_state.edit_redo.append((sess_u, timetable.assignment.get(sess_u)))
        timetable.assignment[sess_u] = old_val
        st.session_state.report = count_violations(timetable, dataset, config)
        st.info("Reverted previous edit.")
        st.rerun()

    # Feasible slots suggestion
    if btn_sugg:
        from core.csp import build_domains
        from core.constraints import count_conflicts_for_assignment
        domains = build_domains(dataset, config)
        domain = domains.get(selected_session, [])
        valid_slots = []
        for val in domain:
            temp_assign = dict(timetable.assignment)
            del temp_assign[selected_session]
            if count_conflicts_for_assignment(selected_session, val, temp_assign, dataset) == 0:
                valid_slots.append(val)

        with st.container(border=True):
            st.markdown(f"##### Feasible Conflict-Free Slots ({len(valid_slots)} Available)")
            if valid_slots:
                st.dataframe(pd.DataFrame([
                    {"Day": ts.day_names[d], "Period": f"Period {p+1}", "Room": r}
                    for d, p, r in valid_slots[:12]
                ]), hide_index=True, use_container_width=True)
            else:
                st.warning("No conflict-free slots found without displacing other sessions.")


# ── Sub-Tool 2: Compare Algorithms ──

def render_tool_compare():
    """GRID 2: Compare Algorithms side-by-side."""
    if st.button("← Back to Manage & Analyze Workspace", key="btn_back_ws_comp"):
        st.session_state.stage4_tool = None
        st.rerun()

    st.markdown("### Compare Algorithms")
    st.caption("Benchmark optimization algorithms side-by-side on duration, solution quality, and convergence.")

    dataset = st.session_state.dataset
    config = st.session_state.config

    with st.container(border=True):
        st.markdown("#### Select Algorithms to Compare")
        algos = st.multiselect(
            "Select Algorithms",
            list(SOLVERS.keys()),
            default=["BT (Heuristics)", "Min-Conflicts", "Simulated Annealing"],
            key="cmp_algos",
        )
        c_r1, c_r2 = st.columns([1, 4])
        with c_r1:
            btn_run = st.button("Run Comparison", type="primary", key="btn_cmp_run")
        with c_r2:
            if st.session_state.get("compare_results"):
                if st.button("Clear Results", key="btn_cmp_clear"):
                    st.session_state.compare_results = None
                    st.rerun()

    if btn_run:
        if not algos:
            st.warning("Select at least one algorithm.")
            return

        prog_bar = st.progress(0.0)
        status_txt = st.empty()

        def comp_callback(p, msg=""):
            prog_bar.progress(min(max(p, 0.0), 1.0))
            status_txt.text(f"Running comparison: {msg or 'Optimizing...'} ({min(p * 100, 100):.0f}%)")

        try:
            results_map = run_experiments(
                dataset, "compare", num_runs=1, output_dir="results",
                config=config, selected_algorithms=algos,
                progress_callback=comp_callback,
                run_ablation=False,
            )
            st.session_state.compare_results = results_map
        except Exception as e:
            prog_bar.empty()
            status_txt.empty()
            st.error(f"Comparison error: {e}")
            import traceback
            st.code(traceback.format_exc(), language="text")
            return

        prog_bar.empty()
        status_txt.empty()

    res = st.session_state.get("compare_results")
    if not res:
        st.caption("Select algorithms above and click **Run Comparison**.")
        return

    # Comparison summary cards
    with st.container(border=True):
        st.markdown("#### Comparison Metrics Overview")
        comp_df = res["comparison_df"]
        cols = st.columns(min(len(comp_df), 4))
        for i, (_, row) in enumerate(comp_df.iterrows()):
            with cols[i % len(cols)]:
                st.metric(
                    f"{row['Algorithm']}",
                    f"{row['Avg Time (s)']}s",
                    f"Soft: {row['Avg Soft Penalty']}",
                )

    with st.container(border=True):
        st.markdown("#### Comparison Table")
        st.dataframe(comp_df, hide_index=True, use_container_width=True)

    # Charts
    chart_path = os.path.join("results", "comparison_compare.png")
    if os.path.exists(chart_path):
        with st.container(border=True):
            st.markdown("#### Execution Speed & Solution Quality Charts")
            st.image(chart_path, use_container_width=True)

    cost_path = os.path.join("results", "cost_iterations_compare.png")
    if os.path.exists(cost_path):
        with st.container(border=True):
            st.markdown("#### Cost Convergence & Iteration Curves")
            st.image(cost_path, use_container_width=True)


# ── Sub-Tool 3: Empirical Benchmark ──

def render_tool_benchmark():
    """GRID 3: Empirical Benchmark with small/large datasets and ablation studies."""
    if st.button("← Back to Manage & Analyze Workspace", key="btn_back_ws_bench"):
        st.session_state.stage4_tool = None
        st.rerun()

    st.markdown("### Empirical Benchmark")
    st.caption("Multi-trial randomized empirical experiments, scalability analysis, and heuristic ablation studies.")

    config = st.session_state.config

    with st.container(border=True):
        st.markdown("#### Benchmark Settings")
        c1, c2, c3 = st.columns(3)
        with c1:
            bench_ds = st.selectbox("Benchmark Dataset", ["Active Dataset", "Small Benchmark (3 Classes)", "Large Benchmark (8 Classes)"], key="bench_ds")
        with c2:
            num_runs = st.number_input("Runs per Randomized Solver", value=10, min_value=1, max_value=20, key="bench_runs")
        with c3:
            run_ablation = st.checkbox("Include Heuristic Ablation (7 configs)", value=True, key="bench_ablation")

        col_b1, col_b2 = st.columns([1, 4])
        with col_b1:
            btn_exp = st.button("Start Benchmark", type="primary", key="btn_bench_start")
        with col_b2:
            if st.session_state.get("experiment_results"):
                if st.button("Clear Benchmark Results", key="btn_bench_clear"):
                    st.session_state.experiment_results = None
                    st.rerun()

    if btn_exp:
        # Determine target dataset
        if "Small" in bench_ds:
            target_ds = parse_dataset(get_small_dataset())
            assign_teachers_and_create_sessions(target_ds, config)
        elif "Large" in bench_ds:
            target_ds = parse_dataset(get_large_dataset())
            assign_teachers_and_create_sessions(target_ds, config)
        else:
            target_ds = st.session_state.dataset

        progress = st.progress(0.0)
        status_text = st.empty()

        def exp_callback(p, msg=""):
            progress.progress(min(max(p, 0.0), 1.0))
            status_text.text(f"Running benchmark: {msg or 'Processing...'} ({min(p * 100, 100):.0f}%)")

        try:
            results_map = run_experiments(
                target_ds, "experiment", num_runs=int(num_runs), output_dir="results",
                config=config,
                progress_callback=exp_callback,
                run_ablation=run_ablation,
            )
            st.session_state.experiment_results = results_map
        except Exception as e:
            progress.empty()
            status_text.empty()
            st.error(f"Benchmark error: {e}")
            import traceback
            st.code(traceback.format_exc(), language="text")
            return

        progress.empty()
        status_text.empty()

    results_map = st.session_state.get("experiment_results")
    if not results_map:
        st.caption("Click **Start Benchmark** to execute multi-trial runs.")
        return

    with st.container(border=True):
        st.markdown("#### Solver Performance Matrix")
        st.dataframe(results_map["comparison_df"], hide_index=True, use_container_width=True)

    if results_map.get("ablation_df") is not None:
        with st.container(border=True):
            st.markdown("#### Heuristic Ablation Study")
            st.caption("Incremental combination of heuristics on Backtracking (Plain, FC, MRV, Degree, AC-3, LCV).")
            st.dataframe(results_map["ablation_df"], hide_index=True, use_container_width=True)

    comp_path = os.path.join("results", "comparison_experiment.png")
    if os.path.exists(comp_path):
        with st.container(border=True):
            st.markdown("#### Performance Comparison Figures")
            st.image(comp_path, use_container_width=True)

    cost_path = os.path.join("results", "cost_iterations_experiment.png")
    if os.path.exists(cost_path):
        with st.container(border=True):
            st.markdown("#### Min-Conflicts & Solver Convergence Curves")
            st.image(cost_path, use_container_width=True)

    analysis_path = os.path.join("results", "analysis_experiment.md")
    if os.path.exists(analysis_path):
        with open(analysis_path, "r", encoding="utf-8") as f:
            analysis_text = f.read()
        with st.container(border=True):
            st.markdown("#### Technical Analysis Report")
            with st.expander("Read Full Analysis Report", expanded=True):
                st.markdown(analysis_text)
            st.download_button(
                "Download Technical Report (.md)",
                analysis_text,
                "class_pilot_analysis.md",
                "text/markdown",
                key="dl_analysis_bench",
            )


# ── Sub-Tool 4: Download & Export ──

def render_tool_export():
    """GRID 4: Download & Export timetables in Excel, PDF, CSV, and JSON."""
    if st.button("← Back to Manage & Analyze Workspace", key="btn_back_ws_exp"):
        st.session_state.stage4_tool = None
        st.rerun()

    st.markdown("### Download & Export")
    st.caption("Export production-ready timetables in Excel, PDF, CSV, and complete JSON archives.")

    if not st.session_state.timetable or not st.session_state.dataset:
        st.info("Please generate a timetable in Stage 2 first before exporting.")
        if st.button("← Go to Stage 2: Generate Timetable", key="btn_goto_s2_exp"):
            st.session_state.current_stage = 2
            st.session_state.stage4_tool = None
            st.rerun()
        return

    timetable = st.session_state.timetable
    dataset = st.session_state.dataset
    config = st.session_state.config

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        with st.container(border=True):
            st.markdown("#### 📗 Excel Workbook")
            st.caption("Multi-sheet Excel workbook with Master grid, Class sheets, Teacher schedules, and Room grids.")
            try:
                excel_data = export_excel(timetable, dataset, config)
                st.download_button(
                    "Download Excel (.xlsx)",
                    excel_data,
                    "class_pilot_timetable.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_excel_btn",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Excel error: {e}")

    with c2:
        with st.container(border=True):
            st.markdown("#### 📕 PDF Document")
            st.caption("Accredited landscape presentation tables ready for institutional distribution.")
            try:
                pdf_data = export_pdf(timetable, dataset)
                st.caption(f"✓ Document ready: {len(dataset.classes)} class schedules ({len(pdf_data)/1024:.1f} KB)")
                st.download_button(
                    "Download PDF (.pdf)",
                    pdf_data,
                    "class_pilot_timetable.pdf",
                    "application/pdf",
                    key="dl_pdf_btn",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"PDF error: {e}")

    with c3:
        with st.container(border=True):
            st.markdown("#### 📘 CSV Records")
            st.caption("Raw tabular records (Class, Subject, Teacher, Day, Period, Room) for database import.")
            csv_data = export_csv(timetable, dataset)
            st.caption(f"✓ Tabular records: {len(timetable.assignment)} scheduled sessions")
            st.download_button(
                "Download CSV (.csv)",
                csv_data,
                "timetable_records.csv",
                "text/csv",
                key="dl_csv_btn",
                use_container_width=True,
            )


    with c4:
        with st.container(border=True):
            st.markdown("#### System State")
            st.caption("Complete model state and assignment mappings for archival preservation.")
            session_data = {
                "dataset": dataset_to_json(dataset),
                "timetable": {
                    s.label(): list(v) for s, v in timetable.assignment.items() if v
                },
            }
            st.download_button(
                "Download State (.json)",
                json.dumps(session_data, indent=2),
                "class_pilot_archive.json",
                "application/json",
                key="dl_json_btn",
                use_container_width=True,
            )

    with st.container(border=True):
        st.markdown("#### Print Preview")
        st.caption("Press Ctrl+P (or Cmd+P) to print the timetable cleanly without headers or action buttons.")
        classes = list(dataset.classes.keys())
        sel_cls = st.selectbox("Select Class for Print Preview", classes, key="print_cls")
        print_html = render_timetable_html(timetable, dataset, "class", sel_cls)
        st.markdown(print_html, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
