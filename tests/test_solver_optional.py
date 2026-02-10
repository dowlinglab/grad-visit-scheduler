from pathlib import Path
import pytest
import pyomo.environ as pyo

from grad_visit_scheduler import scheduler_from_configs, Mode, Solver


def _solver_available(name: str) -> bool:
    if name == "highs":
        return pyo.SolverFactory("appsi_highs").available() or pyo.SolverFactory("highs").available()
    return pyo.SolverFactory(name).available()


@pytest.mark.parametrize(
    ("solver_enum", "solver_name"),
    [
        (Solver.HIGHS, "highs"),
        (Solver.CBC, "cbc"),
        (Solver.GUROBI, "gurobi"),
    ],
)
def test_solver_solve_basic(solver_enum, solver_name):
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
