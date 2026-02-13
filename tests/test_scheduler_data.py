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


def test_build_times_by_building_respects_building_order():
    """Configured building_order should control output ordering."""
    run_cfg = {
        "buildings": {
            "BuildingA": ["1:00-1:25"],
            "BuildingB": ["1:00-1:25"],
        },
        "building_order": ["BuildingB", "BuildingA"],
    }
    times = build_times_by_building(run_cfg)
    assert list(times.keys()) == ["BuildingB", "BuildingA"]


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
    assert s.faculty["External X"]["building"] == "BuildingA"
    assert "External X" in s.requests["Visitor 1"]


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


def test_update_weights_scalar_inputs(tmp_path: Path):
    """Scalar faculty/area weights should broadcast across known fields."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area2"}],
    )
    s = Scheduler(
        times_by_building={"BuildingA": ["1:00-1:25"], "BuildingB": ["1:00-1:25"]},
        student_data_filename=str(csv_path),
        mode=Mode.BUILDING_A_FIRST,
        solver=Solver.HIGHS,
        faculty_catalog={
            "Faculty A": {
                "building": "BuildingA",
                "room": "101",
                "areas": ["Area1", "Area2"],
                "status": "active",
            }
        },
    )
    s.update_weights(faculty_weight=2.0, area_weight=0.5, base_weight=0.1)
    assert set(s.faculty_weights.keys()) == set(s.faculty_fields)
    assert all(v == 2.0 for v in s.faculty_weights.values())
    assert set(s.area_weights.keys()) == set(s.area_fields)
    assert all(v == 0.5 for v in s.area_weights.values())


def test_update_weights_invalid_types_raise(tmp_path: Path):
    """Invalid types for faculty/area weights should raise ValueError."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area2"}],
    )
    s = Scheduler(
        times_by_building={"BuildingA": ["1:00-1:25"], "BuildingB": ["1:00-1:25"]},
        student_data_filename=str(csv_path),
        mode=Mode.BUILDING_A_FIRST,
        solver=Solver.HIGHS,
        faculty_catalog={
            "Faculty A": {
                "building": "BuildingA",
                "room": "101",
                "areas": ["Area1", "Area2"],
                "status": "active",
            }
        },
    )
    with pytest.raises(ValueError, match="faculty_weight"):
        s.update_weights(faculty_weight=["bad"])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="area_weight"):
        s.update_weights(area_weight=["bad"])  # type: ignore[arg-type]


def test_include_all_legacy_faculty_from_catalog(tmp_path: Path):
    """include_legacy_faculty=True should merge all legacy entries into faculty."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area2"}],
    )
    s = Scheduler(
        times_by_building={"BuildingA": ["1:00-1:25"], "BuildingB": ["1:00-1:25"]},
        student_data_filename=str(csv_path),
        mode=Mode.BUILDING_A_FIRST,
        solver=Solver.HIGHS,
        include_legacy_faculty=True,
        faculty_catalog={
            "Faculty A": {
                "building": "BuildingA",
                "room": "101",
                "areas": ["Area1"],
                "status": "active",
            },
            "Legacy L": {
                "building": "BuildingB",
                "room": "201",
                "areas": ["Area2"],
                "status": "legacy",
            },
        },
    )
    assert "Legacy L" in s.faculty
