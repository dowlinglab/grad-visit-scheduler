"""Optional solver integration tests."""

import os
import shutil
from pathlib import Path
import pytest
import pyomo.environ as pyo
from pyomo.common.errors import ApplicationError

from grad_visit_scheduler import scheduler_from_configs, Mode, Solver
from pyomo.opt import TerminationCondition


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
    exe_path = _find_gurobi_iis_executable()
    if exe_path is None:
        return False
    try:
        return pyo.SolverFactory(str(exe_path), solver_io="nl").available(exception_flag=False)
    except Exception:
        return False


def _find_gurobi_iis_executable() -> Path | None:
    """Best-effort lookup for gurobi_ampl executable used by IIS tests."""
    # 1) Explicit env var
    env_exe = os.environ.get("GVS_GUROBI_IIS_EXECUTABLE")
    if env_exe:
        p = Path(env_exe)
        if p.exists():
            return p

    # 2) In PATH
    which_exe = shutil.which("gurobi_ampl")
    if which_exe:
        return Path(which_exe)

    # 3) Common local location used by this project author
    home_candidate = Path.home() / "GitHub" / "Teaching" / "grad-visit-scheduling" / "ampl" / "gurobi_ampl"
    if home_candidate.exists():
        return home_candidate

    # 4) Repo-local fallback
    repo_candidate = Path(__file__).parents[1] / "ampl" / "gurobi_ampl"
    if repo_candidate.exists():
        return repo_candidate

    return None


def _ensure_gurobi_iis_env():
    """Populate env var if an IIS executable is discoverable."""
    if os.environ.get("GVS_GUROBI_IIS_EXECUTABLE"):
        return
    exe_path = _find_gurobi_iis_executable()
    if exe_path is not None:
        os.environ["GVS_GUROBI_IIS_EXECUTABLE"] = str(exe_path)


def _gurobi_iis_solver_ready() -> bool:
    """Return whether executable is discoverable and solver interface is available."""
    _ensure_gurobi_iis_env()
    exe_path = _find_gurobi_iis_executable()
    if exe_path is None:
        return False
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
    assert s.last_solution_set is None
    assert s.last_termination_condition in {TerminationCondition.optimal, TerminationCondition.feasible}


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

    assert 1 <= len(top) <= 3
    objectives = [sol.objective_value for sol in top.solutions]
    assert objectives == sorted(objectives, reverse=True)
    assert all(sol.rank == i for i, sol in enumerate(top.solutions, start=1))
    assert all(sol.termination_condition.lower() in {"optimal", "feasible"} for sol in top.solutions)
    assert all(sol.solver_status.lower() == "ok" for sol in top.solutions)

    seen = set()
    for sol in top.solutions:
        assert sol.active_meetings not in seen
        seen.add(sol.active_meetings)
        assert len(sol.active_meetings) > 0

    # One no-good cut is added after each discovered solution.
    assert hasattr(s.model, "no_good_cuts")
    assert len(s.model.no_good_cuts) == len(top)


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
    assert len(top) >= 1

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
    assert summary["rank"].tolist() == list(range(1, len(top) + 1))
    assert report["plotted_ranks"] == tuple(r for r in (1, 2) if r <= len(top))

    for rel in report["visitor_plot_files"]:
        path = tmp_path / rel
        assert path.exists()
        assert path.stat().st_size > 0
        assert "summary_helper_rank" in path.name
    for rel in report["faculty_plot_files"]:
        path = tmp_path / rel
        assert path.exists()
        assert path.stat().st_size > 0
        assert "summary_helper_rank" in path.name


def test_solver_gurobi_iis_infeasible_path():
    """Run GUROBI_IIS on an infeasible toy case when executable is available."""
    if not _gurobi_iis_solver_ready():
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
    iis_items = list(s.model.iis.items())
    assert len(iis_items) > 0
    iis_names = [comp.name for comp, _ in iis_items]
    assert any(name.startswith("min_visitors_constraint[") for name in iis_names)
    assert any(name.startswith("y[") for name in iis_names)
