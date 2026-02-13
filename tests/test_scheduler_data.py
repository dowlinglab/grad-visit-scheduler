"""Scheduler data and preprocessing tests."""

from pathlib import Path

import pandas as pd
import pytest

from grad_visit_scheduler import Scheduler, Mode, Solver, compute_min_travel_lags
from grad_visit_scheduler.core import slot2min
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


def test_single_building_movement_none_supported(tmp_path: Path):
    """One-building schedules should work with movement policy set to none."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area2"}],
    )
    s = Scheduler(
        times_by_building={"BuildingA": ["1:00-1:25", "1:30-1:55"]},
        student_data_filename=str(csv_path),
        movement={"policy": "none", "phase_slot": {"BuildingA": 1}},
        solver=Solver.HIGHS,
        faculty_catalog={
            "Faculty A": {
                "building": "BuildingA",
                "room": "101",
                "areas": ["Area1"],
                "status": "active",
            }
        },
    )
    assert s.buildings == ["BuildingA"]
    assert s.movement_policy == "none"
    assert s.building_phase_slot["BuildingA"] == 1


def test_three_building_close_proximity_supported(tmp_path: Path):
    """Three-building schedules should accept no-travel movement config."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [{"Name": "Visitor 1", "Prof1": "Faculty B", "Area1": "Area1", "Area2": "Area2"}],
    )
    s = Scheduler(
        times_by_building={
            "BuildingA": ["1:00-1:25", "1:30-1:55"],
            "BuildingB": ["1:00-1:25", "1:30-1:55"],
            "BuildingC": ["1:00-1:25", "1:30-1:55"],
        },
        student_data_filename=str(csv_path),
        movement={
            "policy": "none",
            "phase_slot": {"BuildingA": 1, "BuildingB": 1, "BuildingC": 1},
        },
        solver=Solver.HIGHS,
        faculty_catalog={
            "Faculty A": {"building": "BuildingA", "room": "101", "areas": ["Area1"], "status": "active"},
            "Faculty B": {"building": "BuildingB", "room": "201", "areas": ["Area1"], "status": "active"},
            "Faculty C": {"building": "BuildingC", "room": "301", "areas": ["Area1"], "status": "active"},
        },
    )
    assert len(s.buildings) == 3
    assert set(s.building_phase_slot.keys()) == {"BuildingA", "BuildingB", "BuildingC"}


def test_travel_time_policy_builds_in_building_vars(tmp_path: Path):
    """Travel-time movement policy should create occupancy variables in model."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area2"}],
    )
    s = Scheduler(
        times_by_building={
            "BuildingA": ["1:00-1:25", "1:30-1:55", "2:00-2:25"],
            "BuildingB": ["1:00-1:25", "1:30-1:55", "2:00-2:25"],
        },
        student_data_filename=str(csv_path),
        movement={
            "policy": "travel_time",
            "phase_slot": {"BuildingA": 1, "BuildingB": 1},
            "travel_slots": {
                "BuildingA": {"BuildingA": 0, "BuildingB": 1},
                "BuildingB": {"BuildingA": 1, "BuildingB": 0},
            },
        },
        solver=Solver.HIGHS,
        faculty_catalog={
            "Faculty A": {"building": "BuildingA", "room": "101", "areas": ["Area1"], "status": "active"},
            "Faculty B": {"building": "BuildingB", "room": "201", "areas": ["Area2"], "status": "active"},
        },
    )
    s._build_model(
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=2,
        min_faculty=1,
        max_group=1,
        enforce_breaks=False,
    )
    assert hasattr(s.model, "in_building")


def _has_real_time_overlap(solution):
    """Return True if any visitor has overlapping assigned meeting intervals."""
    for visitor in solution.visitors:
        intervals = []
        for meeting_visitor, faculty, slot in solution.active_meetings:
            if meeting_visitor != visitor:
                continue
            building = solution.context.faculty[faculty]["building"]
            start_min, end_min = slot2min(solution.context.times_by_building[building][slot - 1])
            intervals.append((start_min, end_min))
        intervals.sort()
        for i in range(1, len(intervals)):
            if intervals[i][0] < intervals[i - 1][1]:
                return True
    return False


def test_compute_min_travel_lags_shifted_slots_can_require_two():
    """Shifted/nonuniform slot windows can require lag 2 in one direction."""
    times = {
        "MCH": ["1:00-1:25", "1:30-1:55", "2:00-2:25", "2:30-2:55"],
        "NSH": ["1:15-2:05", "1:45-2:35", "2:15-3:05", "2:45-3:35"],
    }
    lags = compute_min_travel_lags(times)
    assert lags["NSH"]["MCH"] >= 2
    assert lags["MCH"]["NSH"] == 0


def test_shifted_starts_with_policy_none_warns_and_can_overlap(tmp_path: Path):
    """Policy none should warn for shifted clocks and can produce overlap."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [
            {"Name": "Visitor 1", "Prof1": "Prof NSH", "Prof2": "Prof MCH", "Area1": "Area1", "Area2": "Area2"},
        ],
    )

    times = {
        "MCH": ["1:00-1:25", "1:30-1:55", "2:00-2:25"],
        "NSH": ["1:15-1:40", "1:45-2:10", "2:15-2:40"],
    }
    faculty_catalog = {
        "Prof MCH": {"building": "MCH", "room": "101", "areas": ["Area1"], "status": "active"},
        "Prof NSH": {"building": "NSH", "room": "201", "areas": ["Area2"], "status": "active"},
    }

    with pytest.warns(UserWarning, match="real-time visitor overlaps"):
        s = Scheduler(
            times_by_building=times,
            student_data_filename=str(csv_path),
            movement={"policy": "none", "phase_slot": {"MCH": 1, "NSH": 2}},
            solver=Solver.HIGHS,
            faculty_catalog=faculty_catalog,
        )

    s.faculty_limited_availability("Prof NSH", [2])
    s.faculty_limited_availability("Prof MCH", [3])
    sol = s.schedule_visitors(
        group_penalty=0.0,
        min_visitors=0,
        max_visitors=2,
        min_faculty=2,
        max_group=1,
        enforce_breaks=False,
        tee=False,
    )
    assert sol is not None
    assert _has_real_time_overlap(sol)


def test_shifted_starts_nonoverlap_time_policy_prevents_overlap(tmp_path: Path):
    """Automatic nonoverlap movement should prevent shifted-clock overlap."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [
            {"Name": "Visitor 1", "Prof1": "Prof NSH", "Prof2": "Prof MCH", "Area1": "Area1", "Area2": "Area2"},
        ],
    )

    times = {
        "MCH": ["1:00-1:25", "1:30-1:55", "2:00-2:25", "2:30-2:55"],
        "NSH": ["1:15-1:40", "1:45-2:10", "2:15-2:40", "2:45-3:10"],
    }
    faculty_catalog = {
        "Prof MCH": {"building": "MCH", "room": "101", "areas": ["Area1"], "status": "active"},
        "Prof NSH": {"building": "NSH", "room": "201", "areas": ["Area2"], "status": "active"},
    }

    s = Scheduler(
        times_by_building=times,
        student_data_filename=str(csv_path),
        movement={"policy": "nonoverlap_time", "phase_slot": {"MCH": 1, "NSH": 2}},
        solver=Solver.HIGHS,
        faculty_catalog=faculty_catalog,
    )
    s.faculty_limited_availability("Prof NSH", [2])
    s.faculty_limited_availability("Prof MCH", [3, 4])
    sol = s.schedule_visitors(
        group_penalty=0.0,
        min_visitors=0,
        max_visitors=2,
        min_faculty=2,
        max_group=1,
        enforce_breaks=False,
        tee=False,
    )
    assert sol is not None
    assert not _has_real_time_overlap(sol)
    assert s.travel_slots["NSH"]["MCH"] >= 1
