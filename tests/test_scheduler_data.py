"""Scheduler data and preprocessing tests."""

from pathlib import Path

import pandas as pd
import pytest

from grad_visit_scheduler import Scheduler, Mode, Solver
from grad_visit_scheduler.config import build_times_by_building


def _write_csv(path: Path, rows):
    """Write test rows to a CSV file."""
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)


def test_build_times_by_building_includes_breaks():
    """Ensure break slots are preserved in generated time mapping."""
    run_cfg = {
        "buildings": {"BuildingA": ["1:00-1:25"], "BuildingB": ["1:00-1:25"]},
        "breaks": [1],
    }
    times = build_times_by_building(run_cfg)
    assert "breaks" in times
    assert times["breaks"] == [1]


def test_aliases_applied_in_preferences(tmp_path: Path):
    """Ensure faculty aliases are applied while loading visitor requests."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [
            {
                "Name": "Visitor 1",
                "Prof1": "Paulson",
                "Area1": "Area1",
                "Area2": "Area2",
            }
        ],
    )

    times_by_building = {"BuildingA": ["1:00-1:25"], "BuildingB": ["1:00-1:25"]}
    faculty_catalog = {
        "Paulsen": {
            "building": "BuildingB",
            "room": "B022",
            "areas": ["Area1"],
            "status": "active",
        }
    }

    s = Scheduler(
        times_by_building=times_by_building,
        student_data_filename=str(csv_path),
        mode=Mode.NO_OFFSET,
        solver=Solver.HIGHS,
        faculty_catalog=faculty_catalog,
        faculty_aliases={"Paulson": "Paulsen"},
    )

    # Preference should be mapped to Paulsen
    assert "Paulsen" in s.requests["Visitor 1"]


def test_external_faculty_added_from_preferences(tmp_path: Path):
    """Ensure unknown requested names are added as external faculty."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [
            {
                "Name": "Visitor 1",
                "Prof1": "External X",
                "Area1": "Area1",
                "Area2": "Area2",
            }
        ],
    )

    times_by_building = {"BuildingA": ["1:00-1:25"], "BuildingB": ["1:00-1:25"]}
    faculty_catalog = {
        "Faculty A": {
            "building": "BuildingB",
            "room": "101",
            "areas": ["Area1"],
            "status": "active",
        }
    }

    s = Scheduler(
        times_by_building=times_by_building,
        student_data_filename=str(csv_path),
        mode=Mode.NO_OFFSET,
        solver=Solver.HIGHS,
        faculty_catalog=faculty_catalog,
    )

    assert "External X" in s.faculty
    assert s.faculty["External X"]["avail"] == []


def test_faculty_limited_availability_validation(tmp_path: Path):
    """Reject limited-availability slot indices outside valid range."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [
            {
                "Name": "Visitor 1",
                "Prof1": "Faculty A",
                "Area1": "Area1",
                "Area2": "Area2",
            }
        ],
    )

    times_by_building = {"BuildingA": ["1:00-1:25"], "BuildingB": ["1:00-1:25"]}
    faculty_catalog = {
        "Faculty A": {
            "building": "BuildingB",
            "room": "101",
            "areas": ["Area1"],
            "status": "active",
        }
    }

    s = Scheduler(
        times_by_building=times_by_building,
        student_data_filename=str(csv_path),
        mode=Mode.NO_OFFSET,
        solver=Solver.HIGHS,
        faculty_catalog=faculty_catalog,
    )

    with pytest.raises(ValueError):
        s.faculty_limited_availability("Faculty A", [2])
