"""Run the formulation-focused example without installing the package."""

from __future__ import annotations

from pathlib import Path
import os
import sys

# Allow running without installing the package
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from grad_visit_scheduler import scheduler_from_configs, Solver  # noqa: E402

examples = ROOT / "examples"
DOCS_STATIC = ROOT / "docs" / "_static"

s = scheduler_from_configs(
    examples / "faculty_formulation.yaml",
    examples / "config_formulation.yaml",
    examples / "data_formulation_visitors.csv",
    solver=Solver.HIGHS,
)

sol = s.schedule_visitors(
    group_penalty=0.2,
    min_visitors=2,
    max_visitors=8,
    min_faculty=1,
    max_group=2,
    faculty_breaks=1,
    student_breaks=1,
    tee=False,
    run_name="formulation_demo",
)

if sol is not None:
    # Write the canonical quickstart/index figures into docs/_static so rerunning
    # this script refreshes the checked-in documentation assets in one step.
    prev_cwd = Path.cwd()
    DOCS_STATIC.mkdir(parents=True, exist_ok=True)
    os.chdir(DOCS_STATIC)
    try:
        sol.plot_faculty_schedule(
            save_files=True,
            show_solution_rank=False,
            include_rank_in_filename=False,
        )
        sol.plot_visitor_schedule(
            save_files=True,
            show_solution_rank=False,
            include_rank_in_filename=False,
        )
        Path("faculty_schedule_formulation_demo.png").replace("faculty_schedule_example.png")
        Path("visitor_schedule_formulation_demo.png").replace("visitor_schedule_example.png")
        Path("faculty_schedule_formulation_demo.pdf").unlink(missing_ok=True)
        Path("visitor_schedule_formulation_demo.pdf").unlink(missing_ok=True)
    finally:
        os.chdir(prev_cwd)
    print("Feasible solution found.")
else:
    print(s.infeasibility_report())
