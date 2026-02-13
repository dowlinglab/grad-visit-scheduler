"""Optional solver integration tests."""

import os
from pathlib import Path
import pytest
import pyomo.environ as pyo
from pyomo.common.errors import ApplicationError

from grad_visit_scheduler import scheduler_from_configs, Mode, Solver


def _solver_available(name: str) -> bool:
    """Return whether a named Pyomo solver backend is available."""
    try:
        if name == "highs":
            return pyo.SolverFactory("appsi_highs").available() or pyo.SolverFactory("highs").available()
        return pyo.SolverFactory(name).available()
    except ApplicationError:
        return False


def _gurobi_iis_available() -> bool:
    """Return whether GUROBI_IIS backend is available with configured executable."""
    exe = os.environ.get("GVS_GUROBI_IIS_EXECUTABLE", "ampl/gurobi_ampl")
    exe_path = Path(exe)
    if not exe_path.exists():
        return False
    try:
        return pyo.SolverFactory(str(exe_path), solver_io="nl").available(exception_flag=False)
    except Exception:
        return False


@pytest.mark.parametrize(
    ("solver_enum", "solver_name"),
    [
        (Solver.HIGHS, "highs"),
        (Solver.CBC, "cbc"),
        (Solver.GUROBI, "gurobi"),
    ],
)
def test_solver_solve_basic(solver_enum, solver_name):
    """Solve the basic example when the selected solver is installed."""
    if not _solver_available(solver_name):
        pytest.skip(f"Solver '{solver_name}' is not available")

    root = Path(__file__).parents[1]
    s = scheduler_from_configs(
        root / "examples" / "faculty_example.yaml",
        root / "examples" / "config_basic.yaml",
        root / "examples" / "data_fake_visitors.csv",
        mode=Mode.NO_OFFSET,
        solver=solver_enum,
    )
    s.schedule_visitors(
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=4,
        min_faculty=1,
        max_group=2,
        enforce_breaks=True,
        tee=False,
        run_name="test",
    )
    assert s.has_feasible_solution()


def test_solver_top_n_unique_highs():
    """Solve top-N schedules and ensure returned assignments are unique."""
    if not _solver_available("highs"):
        pytest.skip("Solver 'highs' is not available")

    root = Path(__file__).parents[1]
    s = scheduler_from_configs(
        root / "examples" / "faculty_example.yaml",
        root / "examples" / "config_basic.yaml",
        root / "examples" / "data_fake_visitors.csv",
        mode=Mode.NO_OFFSET,
        solver=Solver.HIGHS,
    )

    top = s.schedule_visitors_top_n(
        n_solutions=3,
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=4,
        min_faculty=1,
        max_group=2,
        enforce_breaks=True,
        tee=False,
        run_name="test_top_n",
    )

    assert len(top) >= 1
    objectives = [sol.objective_value for sol in top.solutions]
    assert objectives == sorted(objectives, reverse=True)

    seen = set()
    for sol in top.solutions:
        assert sol.active_meetings not in seen
        seen.add(sol.active_meetings)


def test_solver_top_n_summary_helper_highs(tmp_path: Path):
    """Verify summarize helper returns expected tables and output files."""
    if not _solver_available("highs"):
        pytest.skip("Solver 'highs' is not available")

    root = Path(__file__).parents[1]
    s = scheduler_from_configs(
        root / "examples" / "faculty_example.yaml",
        root / "examples" / "config_basic.yaml",
        root / "examples" / "data_fake_visitors.csv",
        mode=Mode.NO_OFFSET,
        solver=Solver.HIGHS,
    )

    top = s.schedule_visitors_top_n(
        n_solutions=2,
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=4,
        min_faculty=1,
        max_group=2,
        enforce_breaks=True,
        tee=False,
        run_name="test_top_n_summary",
    )
    if len(top) == 0:
        pytest.skip("No feasible solution returned for top-N summary test")

    cwd = Path.cwd()
    try:
        # Keep generated files inside pytest temp area.
        os.chdir(tmp_path)
        report = top.summarize(
            ranks_to_plot=(1, 2),
            save_files=True,
            show_solution_rank=True,
            plot_prefix="summary_helper",
            export_docx=False,
        )
    finally:
        os.chdir(cwd)

    assert "summary" in report
    assert "compact" in report
    assert "visitor_plot_files" in report
    assert "faculty_plot_files" in report

    summary = report["summary"]
    compact = report["compact"]
    assert "objective_value" in summary.columns
    assert "num_assignments" in summary.columns
    assert "objective_gap_from_best" in compact.columns

    for rel in report["visitor_plot_files"]:
        assert (tmp_path / rel).exists()
    for rel in report["faculty_plot_files"]:
        assert (tmp_path / rel).exists()


def test_solver_gurobi_iis_infeasible_path():
    """Run GUROBI_IIS on an infeasible toy case when executable is available."""
    if not _gurobi_iis_available():
        pytest.skip("GUROBI_IIS executable/backend is not available")

    root = Path(__file__).parents[1]
    s = scheduler_from_configs(
        root / "examples" / "faculty_example.yaml",
        root / "examples" / "config_basic.yaml",
        root / "examples" / "data_fake_visitors.csv",
        mode=Mode.NO_OFFSET,
        solver=Solver.GUROBI_IIS,
    )
    s.schedule_visitors(
        group_penalty=0.1,
        min_visitors=20,
        max_visitors=20,
        min_faculty=1,
        max_group=1,
        enforce_breaks=True,
        tee=False,
        run_name="test_iis",
    )
    assert hasattr(s.model, "iis")
    assert not s.has_feasible_solution()
