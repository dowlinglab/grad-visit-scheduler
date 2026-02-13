"""Run the formulation-focused example without installing the package."""

from __future__ import annotations

from pathlib import Path
import sys

# Allow running without installing the package
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from grad_visit_scheduler import scheduler_from_configs, Solver  # noqa: E402

examples = ROOT / "examples"

s = scheduler_from_configs(
    examples / "faculty_formulation.yaml",
    examples / "config_formulation.yaml",
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
    run_name="formulation_demo",
)

if s.has_feasible_solution():
    s.show_faculty_schedule(save_files=True)
    s.show_visitor_schedule(save_files=True)
    print("Feasible solution found.")
else:
    print(s.infeasibility_report())
