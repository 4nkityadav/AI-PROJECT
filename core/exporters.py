"""
exporters.py — Export timetables to CSV, Excel, and PDF.

Each format creates views by class, by teacher, and by room.
"""

from __future__ import annotations
import io
import logging
from collections import defaultdict

import pandas as pd

from core.models import Dataset, Timetable, SolverConfig
from core.constraints import count_violations

logger = logging.getLogger(__name__)


def timetable_to_grid_df(
    timetable: Timetable, dataset: Dataset,
    view_type: str = "class", filter_value: str = "",
) -> pd.DataFrame:
    """
    Convert a timetable to a grid DataFrame for display.
    view_type: "class", "teacher", or "room"
    filter_value: which class/teacher/room to show

    Returns DataFrame with days as rows and periods as columns.
    """
    ts = dataset.time_structure
    days = ts.day_names
    periods = [f"Period {p+1}" for p in range(ts.periods_per_day)]

    grid = {day: {period: "" for period in periods} for day in days}

    for session, value in timetable.assignment.items():
        if value is None:
            continue
        day, period, room_name = value

        # Check if this session matches the filter
        show = False
        if view_type == "class" and session.class_name == filter_value:
            show = True
            entry = f"{session.subject_code}\n{session.teacher_name}\n[{room_name}]"
        elif view_type == "teacher" and session.teacher_name == filter_value:
            show = True
            entry = f"{session.subject_code}\n{session.class_name}\n[{room_name}]"
        elif view_type == "room" and room_name == filter_value:
            show = True
            entry = f"{session.subject_code}\n{session.class_name}\n{session.teacher_name}"

        if show:
            for p_off in range(session.block_size):
                p = period + p_off
                if p < ts.periods_per_day:
                    day_name = days[day]
                    period_name = periods[p]
                    if grid[day_name][period_name]:
                        grid[day_name][period_name] += " | " + entry
                    else:
                        grid[day_name][period_name] = entry

    df = pd.DataFrame(grid).T
    df.index.name = "Day"
    return df


def master_timetable_grid_df(
    timetable: Timetable, dataset: Dataset, group_by: str = "class"
) -> pd.DataFrame:
    """
    Generate an institution-wide Master Grid showing all entities across time slots.
    group_by: 'class' (columns=classes) or 'room' (columns=rooms)
    """
    ts = dataset.time_structure
    entities = list(dataset.classes.keys()) if group_by == "class" else list(dataset.rooms.keys())

    rows = []
    index_labels = []
    for day_idx, day_name in enumerate(ts.day_names):
        for p in range(ts.periods_per_day):
            slot_label = f"{day_name} P{p+1}"
            index_labels.append(slot_label)
            row_dict = {ent: "" for ent in entities}

            for session, val in timetable.assignment.items():
                if val is None:
                    continue
                s_day, s_period, s_room = val
                for p_off in range(session.block_size):
                    if s_day == day_idx and (s_period + p_off) == p:
                        if group_by == "class":
                            if session.class_name in row_dict:
                                entry = f"{session.subject_code} ({session.teacher_name}, {s_room})"
                                if row_dict[session.class_name]:
                                    row_dict[session.class_name] += " | " + entry
                                else:
                                    row_dict[session.class_name] = entry
                        else:
                            if s_room in row_dict:
                                entry = f"{session.subject_code} ({session.class_name}, {session.teacher_name})"
                                if row_dict[s_room]:
                                    row_dict[s_room] += " | " + entry
                                else:
                                    row_dict[s_room] = entry
            rows.append(row_dict)

    df = pd.DataFrame(rows, index=index_labels)
    df.index.name = "Slot"
    return df


def export_csv(timetable: Timetable, dataset: Dataset) -> str:
    """Export the full timetable to CSV format."""
    ts = dataset.time_structure
    rows = []

    for session, value in timetable.assignment.items():
        if value is None:
            continue
        day, period, room_name = value
        rows.append({
            "Class": session.class_name,
            "Subject": session.subject_code,
            "Teacher": session.teacher_name,
            "Day": ts.day_names[day],
            "Day_Index": day,
            "Period": period + 1,
            "Room": room_name,
            "Type": dataset.subjects[session.subject_code].subject_type if session.subject_code in dataset.subjects else "",
            "Block_Size": session.block_size,
        })

    df = pd.DataFrame(rows)
    df = df.sort_values(["Class", "Day_Index", "Period"])
    return df.to_csv(index=False)


def export_excel(timetable: Timetable, dataset: Dataset, config: SolverConfig | None = None) -> bytes:
    """
    Export timetable to Excel with multiple sheets:
    - One sheet per class (grid view)
    - One sheet per teacher (grid view)
    - One sheet per room (grid view)
    - Summary sheet
    - Violations sheet
    """
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Class sheets
        for cls_name in dataset.classes:
            df = timetable_to_grid_df(timetable, dataset, "class", cls_name)
            sheet_name = f"Class_{cls_name}"[:31]  # Excel sheet name limit
            df.to_excel(writer, sheet_name=sheet_name)

        # Teacher sheets
        for t_name in dataset.teachers:
            df = timetable_to_grid_df(timetable, dataset, "teacher", t_name)
            sheet_name = f"Teacher_{t_name}"[:31]
            df.to_excel(writer, sheet_name=sheet_name)

        # Room sheets
        for r_name in dataset.rooms:
            df = timetable_to_grid_df(timetable, dataset, "room", r_name)
            sheet_name = f"Room_{r_name}"[:31]
            df.to_excel(writer, sheet_name=sheet_name)

        # Summary sheet
        summary_data = {
            "Metric": ["Total Sessions", "Classes", "Teachers", "Rooms",
                        "Days", "Periods/Day"],
            "Value": [len(timetable.assignment), len(dataset.classes),
                      len(dataset.teachers), len(dataset.rooms),
                      dataset.time_structure.working_days,
                      dataset.time_structure.periods_per_day],
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary", index=False)

        # Violations sheet
        if config is None:
            config = SolverConfig()
        report = count_violations(timetable, dataset, config)
        v_rows = []
        for v in report.hard_violations + report.soft_violations:
            v_rows.append({"Code": v.code, "Message": v.message, "Day": v.day + 1, "Period": v.period + 1})
        if v_rows:
            pd.DataFrame(v_rows).to_excel(writer, sheet_name="Violations", index=False)
        else:
            pd.DataFrame({"Status": ["No violations found"]}).to_excel(
                writer, sheet_name="Violations", index=False)

    return output.getvalue()


def _generate_pure_pdf_fallback(timetable: Timetable, dataset: Dataset) -> bytes:
    """
    Pure-Python fallback generator that outputs a 100% valid, standards-compliant
    PDF 1.4 document without any third-party dependencies.
    Draws headers, metadata, and grid lines for each class on landscape pages.
    """
    ts = dataset.time_structure
    days = ts.day_names
    num_periods = ts.periods_per_day
    classes = list(dataset.classes.keys())
    if not classes:
        classes = ["Schedule"]

    page_width = 842  # A4 landscape points
    page_height = 595
    margin_x = 40
    margin_top = 40

    def escape_pdf(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    objects: list[bytes] = []

    def add_object(content: str | bytes) -> int:
        if isinstance(content, str):
            content = content.encode("latin1", "replace")
        objects.append(content)
        return len(objects)

    # Object 1: Font
    font_id = add_object(
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    )
    # Object 2: Bold Font
    bold_font_id = add_object(
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"
    )

    page_ids: list[int] = []
    # Placeholder for Pages catalog (Object 3)
    pages_obj_index = len(objects)
    objects.append(b"")  # will fill later

    for cls_name in classes:
        # Build grid data
        df = timetable_to_grid_df(timetable, dataset, "class", cls_name)
        lunch_slot = dataset.classes[cls_name].lunch_break_slot if cls_name in dataset.classes else -1

        # Stream commands
        stream_cmds: list[str] = []

        # Background header banner
        stream_cmds.append("0.12 0.16 0.23 rg")  # #1E293B
        stream_cmds.append(f"{margin_x} {page_height - margin_top - 46} {page_width - 2 * margin_x} 46 re f")

        # Header Text
        stream_cmds.append("BT")
        stream_cmds.append("/F2 16 Tf")
        stream_cmds.append("1 1 1 rg")
        stream_cmds.append(f"{margin_x + 14} {page_height - margin_top - 24} Td")
        stream_cmds.append(f"({escape_pdf('CLASS PILOT — ACADEMIC TIMETABLE: ' + cls_name)}) Tj")
        stream_cmds.append("ET")

        # Subtitle Text
        stream_cmds.append("BT")
        stream_cmds.append("/F1 9 Tf")
        stream_cmds.append("0.85 0.90 0.95 rg")
        stream_cmds.append(f"{margin_x + 14} {page_height - margin_top - 38} Td")
        sub_info = f"Generated by Class Pilot AI Engine  |  Working Days: {ts.working_days}  |  Periods: {num_periods} per day"
        stream_cmds.append(f"({escape_pdf(sub_info)}) Tj")
        stream_cmds.append("ET")

        # Table dimensions
        table_top = page_height - margin_top - 62
        table_left = margin_x
        table_width = page_width - 2 * margin_x
        day_col_w = 75
        period_col_w = (table_width - day_col_w) / max(1, num_periods)
        header_h = 24
        num_days = len(days)
        row_h = min(68, (table_top - 40 - header_h) / max(1, num_days))

        # Table Header background
        stream_cmds.append("0.20 0.25 0.35 rg")
        stream_cmds.append(f"{table_left} {table_top - header_h} {table_width} {header_h} re f")

        # Table Header Text
        stream_cmds.append("BT")
        stream_cmds.append("/F2 9 Tf")
        stream_cmds.append("1 1 1 rg")
        stream_cmds.append(f"{table_left + 8} {table_top - 16} Td")
        stream_cmds.append("(DAY) Tj")
        stream_cmds.append("ET")

        for p in range(num_periods):
            p_label = f"PERIOD {p+1}"
            if p == lunch_slot:
                p_label += " (LUNCH)"
            stream_cmds.append("BT")
            stream_cmds.append("/F2 8 Tf")
            stream_cmds.append("1 1 1 rg")
            stream_cmds.append(f"{table_left + day_col_w + p * period_col_w + 6} {table_top - 16} Td")
            stream_cmds.append(f"({escape_pdf(p_label)}) Tj")
            stream_cmds.append("ET")

        # Table Rows
        for d_idx, day_name in enumerate(days):
            y_row_top = table_top - header_h - d_idx * row_h
            y_row_bot = y_row_top - row_h

            # Alternate row background
            if d_idx % 2 == 1:
                stream_cmds.append("0.97 0.98 0.99 rg")
                stream_cmds.append(f"{table_left} {y_row_bot} {table_width} {row_h} re f")

            # Day column fill
            stream_cmds.append("0.93 0.95 0.97 rg")
            stream_cmds.append(f"{table_left} {y_row_bot} {day_col_w} {row_h} re f")

            # Day text
            stream_cmds.append("BT")
            stream_cmds.append("/F2 9 Tf")
            stream_cmds.append("0.15 0.20 0.30 rg")
            stream_cmds.append(f"{table_left + 8} {y_row_top - row_h / 2 - 3} Td")
            stream_cmds.append(f"({escape_pdf(day_name)}) Tj")
            stream_cmds.append("ET")

            # Period cells
            for p in range(num_periods):
                p_left = table_left + day_col_w + p * period_col_w
                col_name = f"Period {p+1}"
                raw_cell = df.loc[day_name, col_name] if day_name in df.index and col_name in df.columns else ""
                
                if p == lunch_slot and not raw_cell:
                    stream_cmds.append("0.95 0.95 0.95 rg")
                    stream_cmds.append(f"{p_left + 1} {y_row_bot + 1} {period_col_w - 2} {row_h - 2} re f")
                    stream_cmds.append("BT")
                    stream_cmds.append("/F1 7.5 Tf")
                    stream_cmds.append("0.5 0.5 0.5 rg")
                    stream_cmds.append(f"{p_left + 6} {y_row_top - row_h / 2 - 3} Td")
                    stream_cmds.append("(LUNCH BREAK) Tj")
                    stream_cmds.append("ET")
                elif raw_cell:
                    lines = [line.strip() for line in str(raw_cell).split("\n") if line.strip()]
                    # Cell card fill
                    stream_cmds.append("0.92 0.96 1.0 rg")
                    stream_cmds.append(f"{p_left + 2} {y_row_bot + 2} {period_col_w - 4} {row_h - 4} re f")
                    
                    # Left accent bar
                    stream_cmds.append("0.15 0.40 0.85 rg")
                    stream_cmds.append(f"{p_left + 2} {y_row_bot + 2} 3 {row_h - 4} re f")

                    # Cell text lines
                    y_cursor = y_row_top - 14
                    for l_idx, line in enumerate(lines[:3]):
                        font_tag = "/F2" if l_idx == 0 else "/F1"
                        font_sz = "8" if l_idx == 0 else "7"
                        text_col = "0.08 0.15 0.40 rg" if l_idx == 0 else "0.25 0.30 0.40 rg"
                        stream_cmds.append("BT")
                        stream_cmds.append(f"{font_tag} {font_sz} Tf")
                        stream_cmds.append(text_col)
                        stream_cmds.append(f"{p_left + 8} {y_cursor} Td")
                        stream_cmds.append(f"({escape_pdf(line[:22])}) Tj")
                        stream_cmds.append("ET")
                        y_cursor -= 12

        # Grid lines
        stream_cmds.append("0.80 0.84 0.88 RG")  # line color
        stream_cmds.append("0.5 w")
        # Outer box
        stream_cmds.append(f"{table_left} {table_top - header_h - num_days * row_h} {table_width} {header_h + num_days * row_h} re S")
        # Vertical divider for Day
        stream_cmds.append(f"{table_left + day_col_w} {table_top - header_h - num_days * row_h} m {table_left + day_col_w} {table_top} l S")
        # Vertical dividers for periods
        for p in range(1, num_periods):
            px = table_left + day_col_w + p * period_col_w
            stream_cmds.append(f"{px} {table_top - header_h - num_days * row_h} m {px} {table_top} l S")
        # Horizontal dividers
        for d_idx in range(num_days + 1):
            py = table_top - header_h - d_idx * row_h
            stream_cmds.append(f"{table_left} {py} m {table_left + table_width} {py} l S")

        # Footer
        stream_cmds.append("BT")
        stream_cmds.append("/F1 8 Tf")
        stream_cmds.append("0.55 0.60 0.65 rg")
        stream_cmds.append(f"{margin_x} 20 Td")
        stream_cmds.append(f"({escape_pdf('Class Pilot — Automated Institutional Timetable Scheduler | Accredited Schedule Document')}) Tj")
        stream_cmds.append("ET")

        content_bytes = "\n".join(stream_cmds).encode("latin1", "replace")
        stream_obj_id = add_object(
            f"<< /Length {len(content_bytes)} >>\nstream\n".encode("latin1") + content_bytes + b"\nendstream"
        )

        page_obj_id = add_object(
            f"<< /Type /Page /Parent 3 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Resources << /Font << /F1 {font_id} 0 R /F2 {bold_font_id} 0 R >> >> "
            f"/Contents {stream_obj_id} 0 R >>"
        )
        page_ids.append(page_obj_id)

    # Fill Pages object (Object 3)
    kids_str = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[pages_obj_index] = (
        f"<< /Type /Pages /Kids [{kids_str}] /Count {len(page_ids)} >>".encode("latin1")
    )

    # Object Catalog
    catalog_id = add_object("<< /Type /Catalog /Pages 3 0 R >>")

    # Assemble PDF with cross-reference table
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []

    for i, obj in enumerate(objects):
        offsets.append(out.tell())
        out.write(f"{i + 1} 0 obj\n".encode("latin1"))
        out.write(obj)
        out.write(b"\nendobj\n")

    xref_start = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode("latin1"))
    out.write(b"0000000000 65535 f \n")
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode("latin1"))

    out.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n".encode("latin1")
    )
    return out.getvalue()


def export_pdf(timetable: Timetable, dataset: Dataset) -> bytes:
    """
    Export timetable to high-quality PDF with institutional styling.
    Uses reportlab when available, and seamlessly falls back to the
    built-in pure-Python PDF 1.4 vector generator.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, KeepTogether
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        output = io.BytesIO()
        # Page size: A4 landscape (841.89 x 595.28 pt)
        page_w, page_h = landscape(A4)
        margin = 32
        printable_w = page_w - (2 * margin)

        doc = SimpleDocTemplate(
            output,
            pagesize=landscape(A4),
            leftMargin=margin,
            rightMargin=margin,
            topMargin=margin,
            bottomMargin=margin,
        )
        elements = []
        base_styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "CPTitle",
            parent=base_styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=3,
        )
        subtitle_style = ParagraphStyle(
            "CPSubtitle",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=10,
        )
        cell_subj_style = ParagraphStyle(
            "CPSubj",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#1E3A8A"),
            alignment=TA_CENTER,
        )
        cell_detail_style = ParagraphStyle(
            "CPDetail",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=8.5,
            textColor=colors.HexColor("#334155"),
            alignment=TA_CENTER,
        )
        cell_muted_style = ParagraphStyle(
            "CPMuted",
            parent=base_styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#94A3B8"),
            alignment=TA_CENTER,
        )

        ts = dataset.time_structure
        periods = [f"Period {p+1}" for p in range(ts.periods_per_day)]
        day_col_w = 70
        period_col_w = (printable_w - day_col_w) / max(1, ts.periods_per_day)
        col_widths = [day_col_w] + [period_col_w] * ts.periods_per_day

        classes_list = list(dataset.classes.keys())
        for idx, cls_name in enumerate(classes_list):
            cls_info = dataset.classes[cls_name]
            lunch_slot = cls_info.lunch_break_slot

            # Page Header
            elements.append(Paragraph(f"Class Pilot &bull; Timetable Schedule: {cls_name}", title_style))
            elements.append(Paragraph(
                f"Academic Cohort: {cls_name} &nbsp;|&nbsp; Student Strength: {cls_info.strength} &nbsp;|&nbsp; "
                f"Working Days: {ts.working_days} &nbsp;|&nbsp; Periods/Day: {ts.periods_per_day} &nbsp;|&nbsp; "
                f"Lunch Slot: Period {lunch_slot + 1}",
                subtitle_style
            ))

            # Table Header
            header_cells = [Paragraph("<b>Day / Period</b>", cell_subj_style)]
            for p in range(ts.periods_per_day):
                hdr_label = f"<b>P{p+1}</b>"
                if p == lunch_slot:
                    hdr_label += "<br/><font size=6 color='#CBD5E1'>Lunch</font>"
                header_cells.append(Paragraph(hdr_label, cell_subj_style))

            table_data = [header_cells]
            df = timetable_to_grid_df(timetable, dataset, "class", cls_name)

            for day_name in ts.day_names:
                row = [Paragraph(f"<b>{day_name}</b>", cell_subj_style)]
                for p in range(ts.periods_per_day):
                    raw_val = df.loc[day_name, f"Period {p+1}"] if day_name in df.index and f"Period {p+1}" in df.columns else ""
                    if p == lunch_slot and not raw_val:
                        row.append(Paragraph("Lunch Break", cell_muted_style))
                    elif raw_val:
                        parts = [pt.strip() for pt in str(raw_val).split("\n") if pt.strip()]
                        subj_text = parts[0] if len(parts) > 0 else ""
                        other_text = " &bull; ".join(parts[1:]) if len(parts) > 1 else ""
                        subj_obj = dataset.subjects.get(subj_text)
                        is_lab = bool(subj_obj and subj_obj.subject_type == "lab")
                        
                        color_code = "#065F46" if is_lab else "#1E40AF"
                        badge_label = " [LAB]" if is_lab else ""
                        p_html = (
                            f"<font color='{color_code}'><b>{subj_text}{badge_label}</b></font><br/>"
                            f"<font size=6 color='#475569'>{other_text}</font>"
                        )
                        row.append(Paragraph(p_html, cell_detail_style))
                    else:
                        row.append(Paragraph("—", cell_muted_style))
                table_data.append(row)

            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            t_style = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#F1F5F9")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
            ]
            # Alternate row backgrounds
            for r_i in range(1, len(table_data)):
                bg = colors.HexColor("#F8FAFC") if r_i % 2 == 1 else colors.white
                t_style.append(("BACKGROUND", (1, r_i), (-1, r_i), bg))

            table.setStyle(TableStyle(t_style))
            elements.append(table)

            # Footer space or page break
            if idx < len(classes_list) - 1:
                elements.append(PageBreak())

        doc.build(elements)
        res = output.getvalue()
        if len(res) > 200:
            return res
        return _generate_pure_pdf_fallback(timetable, dataset)

    except Exception as e:
        logger.warning(f"ReportLab PDF export encountered issue ({e}), falling back to vector PDF engine: {e}")
        return _generate_pure_pdf_fallback(timetable, dataset)

