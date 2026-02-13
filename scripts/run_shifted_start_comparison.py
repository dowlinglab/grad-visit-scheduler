"""Compare staggered-start performance for Building A first vs Building B first."""

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


def _solve_with_config(run_config: Path, run_name: str):
    examples = ROOT / "examples"
    scheduler = scheduler_from_configs(
        examples / "faculty_formulation.yaml",
        run_config,
        examples / "data_formulation_visitors.csv",
        solver=Solver.HIGHS,
    )
    scheduler.schedule_visitors(
        group_penalty=0.2,
        min_visitors=2,
        max_visitors=8,
        min_faculty=1,
        max_group=2,
        enforce_breaks=True,
        tee=False,
        run_name=run_name,
    )
    return scheduler


def main():
    examples = ROOT / "examples"
    runs = [
        ("Building A first", examples / "config_shifted_a_first.yaml", "shifted_a_first"),
        ("Building B first", examples / "config_shifted_b_first.yaml", "shifted_b_first"),
    ]

    rows = []
    for label, config_path, run_name in runs:
        s = _solve_with_config(config_path, run_name)
        if not s.has_feasible_solution():
            rows.append({"scenario": label, "feasible": False, "objective": None})
            print(f"{label}: infeasible")
            print(s.infeasibility_report())
            continue

        sol = s._current_solution_result()
        summary = sol.summary_row(best_objective=sol.objective_value)
        rows.append(
            {
                "scenario": label,
                "feasible": True,
                "objective": sol.objective_value,
                "meetings": summary["num_assignments"],
                "requested_meetings": summary["num_requested_assignments"],
                "group_meetings": summary["num_group_slots"],
            }
        )
        sol.plot_visitor_schedule(save_files=True, show_solution_rank=False)
        sol.plot_faculty_schedule(save_files=True, show_solution_rank=False)

    df = pd.DataFrame(rows)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
