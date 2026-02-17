"""Run movement scenarios and print one unified comparison table."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import sys

import pandas as pd

# Allow running without installing the package
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from grad_visit_scheduler import scheduler_from_configs, Solver  # noqa: E402


@dataclass(frozen=True)
class Scenario:
    slug: str
    category: str
    label: str
    faculty_file: str
    run_file: str
    notes: str


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        slug="one_building",
        category="Baseline",
        label="One building (no movement)",
        faculty_file="faculty_one_building.yaml",
        run_file="config_one_building.yaml",
        notes="Single-building baseline.",
    ),
    Scenario(
        slug="two_close_none",
        category="Baseline",
        label="Two buildings (close, policy=none)",
        faculty_file="faculty_formulation.yaml",
        run_file="config_two_buildings_close.yaml",
        notes="Close clocks with no explicit travel lag.",
    ),
    Scenario(
        slug="three_close_none",
        category="Baseline",
        label="Three buildings (close, policy=none)",
        faculty_file="faculty_three_buildings.yaml",
        run_file="config_three_buildings_close.yaml",
        notes="Close clocks with no explicit travel lag.",
    ),
    Scenario(
        slug="two_travel_lag1",
        category="Travel lag",
        label="Two buildings (+1 slot travel lag)",
        faculty_file="faculty_formulation.yaml",
        run_file="config_two_buildings_travel_delay.yaml",
        notes="Manual travel_time matrix with one-slot inter-building lag.",
    ),
    Scenario(
        slug="three_travel_lag1",
        category="Travel lag",
        label="Three buildings (+1 slot travel lag)",
        faculty_file="faculty_three_buildings.yaml",
        run_file="config_three_buildings_travel_delay.yaml",
        notes="Manual travel_time matrix with one-slot inter-building lag.",
    ),
    Scenario(
        slug="shifted_abc_earlier_nonoverlap",
        category="Shifted clocks",
        label="Shifted clocks (ABC starts 15 min earlier)",
        faculty_file="faculty_formulation.yaml",
        run_file="config_shifted_abc_earlier_nonoverlap.yaml",
        notes="nonoverlap_time auto-lag from absolute timestamps.",
    ),
    Scenario(
        slug="shifted_xyz_earlier_nonoverlap",
        category="Shifted clocks",
        label="Shifted clocks (XYZ starts 15 min earlier)",
        faculty_file="faculty_formulation.yaml",
        run_file="config_shifted_xyz_earlier_nonoverlap.yaml",
        notes="nonoverlap_time auto-lag from absolute timestamps.",
    ),
    Scenario(
        slug="staggered_a_first",
        category="Phase slot",
        label="Staggered start (ABC first)",
        faculty_file="faculty_formulation.yaml",
        run_file="config_shifted_a_first.yaml",
        notes="phase_slot offset with policy=none.",
    ),
    Scenario(
        slug="staggered_b_first",
        category="Phase slot",
        label="Staggered start (XYZ first)",
        faculty_file="faculty_formulation.yaml",
        run_file="config_shifted_b_first.yaml",
        notes="phase_slot offset with policy=none.",
    ),
)


@contextmanager
def _pushd(path: Path):
    prev = Path.cwd()
    path.mkdir(parents=True, exist_ok=True)
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def _solve_case(scenario: Scenario, plot_dir: Path | None):
    examples = ROOT / "examples"
    scheduler = scheduler_from_configs(
        examples / scenario.faculty_file,
        examples / scenario.run_file,
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
        run_name=scenario.slug,
    )

    movement_policy = scheduler.movement_policy

    if not scheduler.has_feasible_solution():
        return {
            "category": scenario.category,
            "scenario": scenario.label,
            "slug": scenario.slug,
            "policy": movement_policy,
            "feasible": False,
            "objective": None,
            "assignments": None,
            "requested_assignments": None,
            "group_slots": None,
            "notes": scenario.notes,
        }

    sol = scheduler.current_solution()
    if plot_dir is not None:
        with _pushd(plot_dir):
            visitor_paths = sol.plot_visitor_schedule(
                save_files=True,
                show_solution_rank=False,
                include_rank_in_filename=False,
            )
            faculty_paths = sol.plot_faculty_schedule(
                save_files=True,
                show_solution_rank=False,
                include_rank_in_filename=False,
            )
            if visitor_paths:
                Path(visitor_paths[0]).replace(f"movement_{scenario.slug}_visitor.png")
                Path(visitor_paths[1]).unlink(missing_ok=True)
            if faculty_paths:
                Path(faculty_paths[0]).replace(f"movement_{scenario.slug}_faculty.png")
                Path(faculty_paths[1]).unlink(missing_ok=True)

    row = sol.summary_row(best_objective=sol.objective_value)
    return {
        "category": scenario.category,
        "scenario": scenario.label,
        "slug": scenario.slug,
        "policy": movement_policy,
        "feasible": True,
        "objective": round(float(sol.objective_value), 3),
        "assignments": int(row["num_assignments"]),
        "requested_assignments": int(row["num_requested_assignments"]),
        "group_slots": int(row["num_group_slots"]),
        "notes": scenario.notes,
    }


def run(selected_slugs: list[str] | None = None, plot_dir: Path | None = None) -> pd.DataFrame:
    selected = set(selected_slugs) if selected_slugs else None
    scenarios = [s for s in SCENARIOS if selected is None or s.slug in selected]
    rows = [_solve_case(scenario, plot_dir=plot_dir) for scenario in scenarios]
    return pd.DataFrame(rows)


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--slugs",
        nargs="*",
        default=None,
        help="Optional scenario slugs to run (default: all).",
    )
    parser.add_argument(
        "--plot-dir",
        type=Path,
        default=ROOT / "docs" / "_static",
        help="Directory for output plots. Use --no-plots to skip plot generation.",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip generating plots.",
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    plot_dir = None if args.no_plots else args.plot_dir
    df = run(selected_slugs=args.slugs, plot_dir=plot_dir)
    columns = [
        "category",
        "scenario",
        "policy",
        "feasible",
        "objective",
        "assignments",
        "requested_assignments",
        "group_slots",
    ]
    print(df[columns].to_string(index=False))


if __name__ == "__main__":
    main()
