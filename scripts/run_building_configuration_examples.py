"""Run one-, two-, and three-building movement-policy examples on the large dataset."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

# Allow running without installing the package
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from grad_visit_scheduler import scheduler_from_configs, Solver  # noqa: E402


def _solve_case(label: str, faculty_file: str, run_file: str, run_name: str):
    examples = ROOT / "examples"
    s = scheduler_from_configs(
        examples / faculty_file,
        examples / run_file,
        examples / "data_formulation_visitors.csv",
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
        run_name=run_name,
    )
    if not s.has_feasible_solution():
        return {
            "scenario": label,
            "feasible": False,
            "objective": None,
            "num_assignments": None,
            "num_requested_assignments": None,
            "num_group_slots": None,
        }
    sol = s._current_solution_result()
    row = sol.summary_row(best_objective=sol.objective_value)
    return {
        "scenario": label,
        "feasible": True,
        "objective": sol.objective_value,
        "num_assignments": row["num_assignments"],
        "num_requested_assignments": row["num_requested_assignments"],
        "num_group_slots": row["num_group_slots"],
    }


def main():
    scenarios = [
        ("One building", "faculty_one_building.yaml", "config_one_building.yaml", "cfg_one_building"),
        ("Two buildings (close)", "faculty_formulation.yaml", "config_two_buildings_close.yaml", "cfg_two_close"),
        ("Three buildings (close)", "faculty_three_buildings.yaml", "config_three_buildings_close.yaml", "cfg_three_close"),
    ]
    rows = [_solve_case(*scenario) for scenario in scenarios]
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
