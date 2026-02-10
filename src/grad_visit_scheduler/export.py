"""Export helpers."""
from __future__ import annotations

from pathlib import Path


def export_visitor_docx(
    scheduler,
    filename,
    *,
    building: str | None = None,
    font_name: str = "Arial",
    font_size_pt: int = 11,
    include_breaks: bool = True,
):
    """Write a visitor schedule DOCX for a solved scheduler."""
    if not scheduler.has_feasible_solution():
        raise RuntimeError(
            f"No feasible solution available (termination: {getattr(scheduler, 'last_termination_condition', None)})."
        )

    try:
        from docx import Document
        from docx.shared import Pt
    except Exception as exc:  # pragma: no cover - environment dependent
        raise ImportError("python-docx is required to export schedules to .docx") from exc

    output_path = Path(filename)

    document = Document()

    def format_font(run):
        run.font.size = Pt(font_size_pt)
        run.font.name = font_name

    m = scheduler.model
    if building is None:
        building = next(iter(scheduler.times_by_building))

    times = scheduler.times_by_building[building]

    for visitor in m.visitors:
        p = document.add_paragraph()
        run = p.add_run(visitor)
        format_font(run)

        table = document.add_table(rows=len(m.time), cols=3)

        for i, t in enumerate(m.time):
            row = table.rows[i].cells

            tm = times[t - 1]
            start, end = tm.split("-")
            row[0].text = f"{start.strip()} - {end.strip()} pm"

            faculty = [f for f in m.faculty if m.y[visitor, f, t]() >= 0.5]
            if faculty:
                faculty = faculty[0]
                bldg = scheduler.faculty[faculty]["building"]
                row[1].text = "Prof. " + faculty
                row[2].text = scheduler.faculty[faculty]["room"] + " " + bldg
            elif include_breaks:
                row[1].text = "Break"
                row[2].text = " "

            for j in range(3):
                if row[j].paragraphs and row[j].paragraphs[0].runs:
                    format_font(row[j].paragraphs[0].runs[0])
                elif row[j].paragraphs:
                    run = row[j].paragraphs[0].add_run("")
                    format_font(run)

        document.add_paragraph(" ")

    document.save(str(output_path))
    return output_path
