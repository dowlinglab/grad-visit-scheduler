"""Additional tests for rich SolutionResult/SolutionSet behavior."""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib
import pytest
import pyomo.environ as pyo
from pyomo.common.errors import ApplicationError

from grad_visit_scheduler import (
    Scheduler,
    Mode,
    Solver,
    scheduler_from_configs,
    export_visitor_docx,
)
from grad_visit_scheduler.data import load_visitor_csv

matplotlib.use("Agg")


def _solver_available(name: str) -> bool:
    """Return whether a named Pyomo solver backend is available."""
    try:
        if name == "highs":
            return pyo.SolverFactory("appsi_highs").available() or pyo.SolverFactory("highs").available()
        return pyo.SolverFactory(name).available()
    except ApplicationError:
        return False


def _build_solved_scheduler() -> Scheduler:
    """Build and solve the formulation example with HiGHS."""
    root = Path(__file__).parents[1]
    s = scheduler_from_configs(
        root / "examples" / "faculty_formulation.yaml",
        root / "examples" / "config_formulation.yaml",
        root / "examples" / "data_formulation_visitors.csv",
        mode=Mode.NO_OFFSET,
        solver=Solver.HIGHS,
    )
    s.schedule_visitors(
        group_penalty=0.2,
        min_visitors=2,
        max_visitors=8,
        min_faculty=1,
        max_group=2,
        enforce_breaks=True,
        tee=False,
        run_name="unit",
    )
    return s


def _build_tiny_scheduler(tmp_path: Path, mode: Mode = Mode.BUILDING_A_FIRST) -> Scheduler:
    """Build a tiny scheduler for top-N edge-path tests."""
    csv_path = tmp_path / "visitors.csv"
    csv_path.write_text("Name,Prof1,Area1,Area2\nVisitor 1,Faculty A,Area1,Area1\n", encoding="utf-8")

    times_by_building = {
        "BuildingA": ["1:00-1:25"],
        "BuildingB": ["1:00-1:25"],
    }
    faculty_catalog = {
        "Faculty A": {
            "building": "BuildingA",
            "room": "101",
            "areas": ["Area1"],
            "status": "active",
        }
    }
    return Scheduler(
        times_by_building=times_by_building,
        student_data_filename=str(csv_path),
        mode=mode,
        solver=Solver.HIGHS,
        faculty_catalog=faculty_catalog,
    )


def test_load_visitor_csv(tmp_path: Path):
    """Data helper should read visitor CSV into a DataFrame."""
    path = tmp_path / "v.csv"
    path.write_text("Name,Prof1\nA,X\n", encoding="utf-8")
    df = load_visitor_csv(str(path))
    assert list(df.columns) == ["Name", "Prof1"]
    assert df.iloc[0]["Name"] == "A"


def test_scheduler_data_helpers(tmp_path: Path):
    """Basic data helper methods should mutate scheduler state as expected."""
    s = _build_tiny_scheduler(tmp_path)

    s.add_external_faculty("External Y", building="BuildingB", room="B1", areas=["Area1"], available=[1])
    assert "External Y" in s.faculty
    assert s.faculty["External Y"]["room"] == "B1"

    s.specify_limited_student_availability({"Visitor 1": [1]})
    assert s.students_available["Visitor 1"] == [1]


def test_current_solution_result_raises_before_solve(tmp_path: Path):
    """Accessing current solution snapshot before solve should raise."""
    s = _build_tiny_scheduler(tmp_path)
    with pytest.raises(RuntimeError, match="No feasible solution"):
        s._current_solution_result()


@pytest.mark.skipif(not _solver_available("highs"), reason="HiGHS solver unavailable")
def test_solution_result_single_solution_api(tmp_path: Path):
    """SolutionResult should support summary, plotting, and DOCX export."""
    s = _build_solved_scheduler()
    top = s.schedule_visitors_top_n(
        n_solutions=2,
        group_penalty=0.2,
        min_visitors=2,
        max_visitors=8,
        min_faculty=1,
        max_group=2,
        enforce_breaks=True,
        tee=False,
        run_name="sol_api",
    )
    assert len(top) >= 1

    sol = top.get(1)
    row = sol.summary_row(best_objective=sol.objective_value)
    assert row["rank"] == 1
    assert row["objective_gap_from_best"] == 0.0

    any_meeting = next(iter(sol.active_meetings))
    assert sol.meeting_assigned(*any_meeting)

    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        visitor_paths = sol.plot_visitor_schedule(save_files=True, show_solution_rank=True)
        faculty_paths = sol.plot_faculty_schedule(save_files=True, show_solution_rank=True)
        docx_path = sol.export_visitor_docx("single_solution.docx")
    finally:
        os.chdir(cwd)

    assert visitor_paths is not None
    assert faculty_paths is not None
    assert (tmp_path / visitor_paths[0]).exists()
    assert (tmp_path / faculty_paths[0]).exists()
    assert (tmp_path / docx_path.name).exists()


@pytest.mark.skipif(not _solver_available("highs"), reason="HiGHS solver unavailable")
def test_solution_set_summarize_options(tmp_path: Path):
    """Summarize helper should handle optional arguments and docx export."""
    s = _build_solved_scheduler()
    top = s.schedule_visitors_top_n(
        n_solutions=2,
        group_penalty=0.2,
        min_visitors=2,
        max_visitors=8,
        min_faculty=1,
        max_group=2,
        enforce_breaks=True,
        tee=False,
        run_name="sum_opts",
    )

    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        report = top.summarize(
            compact_columns=["rank", "objective_value", "not_a_column"],
            ranks_to_plot=(1, 99),
            save_files=False,
            export_docx=True,
            docx_prefix="summary_docx",
        )
    finally:
        os.chdir(cwd)

    assert list(report["compact"].columns) == ["rank", "objective_value"]
    assert report["plotted_ranks"] == (1,)
    assert report["visitor_plot_files"] == ()
    assert report["faculty_plot_files"] == ()
    assert len(report["docx_files"]) == len(top)
    for p in report["docx_files"]:
        assert (tmp_path / Path(p).name).exists()


@pytest.mark.skipif(not _solver_available("highs"), reason="HiGHS solver unavailable")
def test_scheduler_legacy_wrappers_emit_futurewarning(tmp_path: Path):
    """Legacy scheduler wrappers should warn and still execute."""
    s = _build_solved_scheduler()

    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        with pytest.warns(FutureWarning):
            s.show_faculty_schedule(save_files=False)
        with pytest.warns(FutureWarning):
            s.show_visitor_schedule(save_files=False)
        with pytest.warns(FutureWarning):
            out = s.export_visitor_docx("legacy.docx")
    finally:
        os.chdir(cwd)

    assert (tmp_path / out.name).exists()


@pytest.mark.skipif(not _solver_available("highs"), reason="HiGHS solver unavailable")
def test_top_level_export_helper_emits_futurewarning(tmp_path: Path):
    """Top-level export helper should warn and export a DOCX file."""
    s = _build_solved_scheduler()

    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        with pytest.warns(FutureWarning):
            out = export_visitor_docx(s, "top_level.docx")
    finally:
        os.chdir(cwd)

    assert (tmp_path / out.name).exists()


@pytest.mark.skipif(not _solver_available("highs"), reason="HiGHS solver unavailable")
def test_show_utility_and_plot_preferences():
    """Utility and preference visual helpers should return matplotlib objects."""
    s = _build_solved_scheduler()
    fig1, ax1 = s.plot_preferences()
    assert fig1 is not None
    assert ax1 is not None

    fig2, ax2 = s.show_utility()
    assert fig2 is not None
    assert ax2 is not None


@pytest.mark.skipif(not _solver_available("highs"), reason="HiGHS solver unavailable")
def test_check_requests_runs(capsys):
    """Request diagnostic should run without raising for solved models."""
    s = _build_solved_scheduler()
    s.check_requests()
    captured = capsys.readouterr()
    assert "visitors with" in captured.out


def test_top_n_invalid_n_raises(tmp_path: Path):
    """Top-N solve should reject n_solutions < 1."""
    s = _build_tiny_scheduler(tmp_path)
    with pytest.raises(ValueError, match="at least 1"):
        s.schedule_visitors_top_n(n_solutions=0)


@pytest.mark.skipif(not _solver_available("highs"), reason="HiGHS solver unavailable")
def test_top_n_returns_fewer_than_requested_when_unique(tmp_path: Path):
    """Top-N should stop early when no more unique feasible schedules exist."""
    s = _build_tiny_scheduler(tmp_path)
    top = s.schedule_visitors_top_n(
        n_solutions=5,
        group_penalty=0.1,
        min_visitors=1,
        max_visitors=1,
        min_faculty=1,
        max_group=1,
        enforce_breaks=False,
        tee=False,
        run_name="tiny",
    )
    assert len(top) == 1


@pytest.mark.skipif(not _solver_available("highs"), reason="HiGHS solver unavailable")
def test_top_n_first_infeasible_path_and_report(tmp_path: Path):
    """If first top-N solve is infeasible, report state should still be populated."""
    s = _build_tiny_scheduler(tmp_path)
    top = s.schedule_visitors_top_n(
        n_solutions=3,
        group_penalty=0.1,
        min_visitors=2,
        max_visitors=2,
        min_faculty=1,
        max_group=1,
        enforce_breaks=False,
        tee=False,
        run_name="tiny_infeasible",
    )
    assert len(top) == 0
    assert not s.has_feasible_solution()
    report = s.infeasibility_report()
    assert "Termination:" in report


def test_infeasibility_report_without_results(tmp_path: Path):
    """Infeasibility report should handle pre-solve state."""
    s = _build_tiny_scheduler(tmp_path)
    assert s.infeasibility_report() == "No solver results available."
