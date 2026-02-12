"""Run a top-N no-good-cut scheduling example without installing the package."""

from __future__ import annotations

from pathlib import Path
import sys

# Allow running without installing the package
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from grad_visit_scheduler import scheduler_from_configs, Mode, Solver  # noqa: E402

examples = ROOT / "examples"

s = scheduler_from_configs(
    examples / "faculty_formulation.yaml",
    examples / "config_formulation.yaml",
    examples / "data_formulation_visitors.csv",
    mode=Mode.NO_OFFSET,
    solver=Solver.HIGHS,
)

top = s.schedule_visitors_top_n(
    n_solutions=3,
    group_penalty=0.2,
    min_visitors=2,
    max_visitors=8,
    min_faculty=1,
    max_group=2,
    enforce_breaks=True,
    tee=False,
    run_name="top_n_demo",
)

if len(top) == 0:
    print(s.infeasibility_report())
else:
    print("Found", len(top), "solution(s).")
    print(top.to_dataframe().to_string(index=False))

    top.plot_faculty_schedule(rank=1, save_files=True)
    top.plot_visitor_schedule(rank=1, save_files=True)

    if len(top) > 1:
        top.plot_faculty_schedule(rank=2, save_files=True)
        top.plot_visitor_schedule(rank=2, save_files=True)

    top.export_visitor_docx_all(prefix="visitor_schedule_top")
