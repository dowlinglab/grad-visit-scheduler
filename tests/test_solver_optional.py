"""Optional solver integration tests."""

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
