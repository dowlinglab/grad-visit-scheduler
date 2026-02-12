"""Export helpers."""
from __future__ import annotations


def export_visitor_docx(
    scheduler,
    filename,
    *,
    solution=None,
    building: str | None = None,
    font_name: str = "Arial",
    font_size_pt: int = 11,
    include_breaks: bool = True,
):
    """Export a solved visitor schedule to a DOCX document.

    Parameters
    ----------
    scheduler:
        Solved scheduler instance containing ``model`` and metadata.
    filename:
        Output DOCX filename.
    solution:
        Optional ``SolutionResult`` snapshot to export. If omitted, uses the
        scheduler's most recently solved model assignment.
    building:
        Building key used to pick displayed time labels. Defaults to the first
        configured building.
    font_name:
        Font family used in the generated document.
    font_size_pt:
        Font size in points.
    include_breaks:
        If ``True``, include explicit "Break" rows for unscheduled slots.

    Returns
    -------
    pathlib.Path
        Path to the written DOCX file.

    Raises
    ------
    RuntimeError
        If the scheduler does not have a feasible solution.
    ImportError
        If ``python-docx`` is not installed.
    """
    chosen = solution if solution is not None else scheduler._current_solution_result()
    return chosen.export_visitor_docx(
        filename,
        building=building,
        font_name=font_name,
        font_size_pt=font_size_pt,
        include_breaks=include_breaks,
    )
