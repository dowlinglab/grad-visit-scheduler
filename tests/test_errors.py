"""Validation and error-path tests."""

from pathlib import Path
import pytest
import pandas as pd

from grad_visit_scheduler import Scheduler, Mode, Solver, scheduler_from_configs
from grad_visit_scheduler.config import load_faculty_catalog, load_run_config, build_times_by_building


def _write_csv(path: Path, rows):
    """Write test rows to a CSV file."""
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)


def test_missing_name_column_raises(tmp_path: Path):
    """Raise when visitor CSV is missing the required ``Name`` column."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(csv_path, [{"Prof1": "Faculty A", "Area1": "Area1"}])

    times_by_building = {"BuildingA": ["1:00-1:25"], "BuildingB": ["1:00-1:25"]}
    faculty_catalog = {
        "Faculty A": {
            "building": "BuildingB",
            "room": "101",
            "areas": ["Area1"],
            "status": "active",
        }
    }

    with pytest.raises(ValueError, match="Name"):
        Scheduler(
            times_by_building=times_by_building,
            student_data_filename=str(csv_path),
            mode=Mode.NO_OFFSET,
            solver=Solver.HIGHS,
            faculty_catalog=faculty_catalog,
        )


def test_duplicate_names_raise(tmp_path: Path):
    """Raise when visitor CSV contains duplicate names."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [
            {"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1"},
            {"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1"},
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

    with pytest.raises(ValueError, match="Duplicate visitor names"):
        Scheduler(
            times_by_building=times_by_building,
            student_data_filename=str(csv_path),
            mode=Mode.NO_OFFSET,
            solver=Solver.HIGHS,
            faculty_catalog=faculty_catalog,
        )


def test_invalid_faculty_status_raises(tmp_path: Path):
    """Raise when faculty catalog includes an invalid status value."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(csv_path, [{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1"}])

    times_by_building = {"BuildingA": ["1:00-1:25"], "BuildingB": ["1:00-1:25"]}
    faculty_catalog = {
        "Faculty A": {
            "building": "BuildingB",
            "room": "101",
            "areas": ["Area1"],
            "status": "unknown",
        }
    }

    with pytest.raises(ValueError, match="Invalid faculty status"):
        Scheduler(
            times_by_building=times_by_building,
            student_data_filename=str(csv_path),
            mode=Mode.NO_OFFSET,
            solver=Solver.HIGHS,
            faculty_catalog=faculty_catalog,
        )


def test_alias_target_missing_raises(tmp_path: Path):
    """Raise when an alias target does not exist in the faculty list."""
    faculty_yaml = tmp_path / "faculty.yaml"
    faculty_yaml.write_text(
        "faculty:\n  Faculty A:\n    building: BuildingB\n    room: '101'\n    areas: ['Area1']\n    status: active\naliases:\n  Alias A: Faculty B\n"
    )

    with pytest.raises(ValueError, match="Alias target"):
        load_faculty_catalog(faculty_yaml)


def test_empty_faculty_catalog_raises(tmp_path: Path):
    """Raise when faculty catalog is missing or has empty faculty section."""
    faculty_yaml = tmp_path / "faculty.yaml"
    faculty_yaml.write_text("faculty: {}\n")
    with pytest.raises(ValueError, match="missing 'faculty' section"):
        load_faculty_catalog(faculty_yaml)


def test_missing_buildings_in_run_config_raises(tmp_path: Path):
    """Raise when run config omits the ``buildings`` section."""
    run_yaml = tmp_path / "run.yaml"
    run_yaml.write_text("breaks: [1]\n")

    with pytest.raises(ValueError, match="buildings"):
        load_run_config(run_yaml)


def test_empty_or_unequal_building_slot_lists_raise(tmp_path: Path):
    """Reject zero-slot buildings and unequal slot counts."""
    empty_run = tmp_path / "empty_run.yaml"
    empty_run.write_text(
        "buildings:\n"
        "  BuildingA: []\n"
        "  BuildingB: ['1:00-1:25']\n"
    )
    with pytest.raises(ValueError, match="at least one time slot"):
        load_run_config(empty_run)

    uneven_run = tmp_path / "uneven_run.yaml"
    uneven_run.write_text(
        "buildings:\n"
        "  BuildingA: ['1:00-1:25']\n"
        "  BuildingB: ['1:00-1:25', '1:30-1:55']\n"
    )
    with pytest.raises(ValueError, match="same number of time slots"):
        load_run_config(uneven_run)


def test_invalid_building_order_shape_raises(tmp_path: Path):
    """Raise when building_order is empty."""
    run_yaml = tmp_path / "run.yaml"
    run_yaml.write_text(
        "buildings:\n"
        "  BuildingA: ['1:00-1:25']\n"
        "  BuildingB: ['1:00-1:25']\n"
        "building_order: []\n"
    )
    with pytest.raises(ValueError, match="non-empty"):
        load_run_config(run_yaml)


def test_invalid_building_order_missing_entries_raises(tmp_path: Path):
    """Raise when building_order references unknown building names."""
    run_yaml = tmp_path / "run.yaml"
    run_yaml.write_text(
        "buildings:\n"
        "  BuildingA: ['1:00-1:25']\n"
        "  BuildingB: ['1:00-1:25']\n"
        "building_order: ['BuildingA', 'BuildingC']\n"
    )
    with pytest.raises(ValueError, match="entries not found"):
        load_run_config(run_yaml)


def test_invalid_movement_policy_raises(tmp_path: Path):
    """Raise when movement.policy is unsupported."""
    run_yaml = tmp_path / "run.yaml"
    run_yaml.write_text(
        "buildings:\n"
        "  BuildingA: ['1:00-1:25']\n"
        "movement:\n"
        "  policy: teleport\n"
    )
    with pytest.raises(ValueError, match="movement.policy"):
        load_run_config(run_yaml)


def test_invalid_movement_config_shapes_raise(tmp_path: Path):
    """Reject non-dict movement and invalid phase-slot shape/building."""
    non_dict = tmp_path / "non_dict.yaml"
    non_dict.write_text(
        "buildings:\n"
        "  BuildingA: ['1:00-1:25']\n"
        "movement: auto\n"
    )
    with pytest.raises(ValueError, match="movement"):
        load_run_config(non_dict)

    bad_phase_type = tmp_path / "bad_phase_type.yaml"
    bad_phase_type.write_text(
        "buildings:\n"
        "  BuildingA: ['1:00-1:25']\n"
        "movement:\n"
        "  policy: none\n"
        "  phase_slot: 1\n"
    )
    with pytest.raises(ValueError, match="phase_slot"):
        load_run_config(bad_phase_type)

    bad_phase_building = tmp_path / "bad_phase_building.yaml"
    bad_phase_building.write_text(
        "buildings:\n"
        "  BuildingA: ['1:00-1:25']\n"
        "movement:\n"
        "  policy: none\n"
        "  phase_slot:\n"
        "    UnknownBuilding: 1\n"
    )
    with pytest.raises(ValueError, match="unknown building"):
        load_run_config(bad_phase_building)


def test_nonoverlap_time_with_explicit_travel_slots_raises(tmp_path: Path):
    """nonoverlap_time policy should not accept manual travel slot matrices."""
    run_yaml = tmp_path / "run.yaml"
    run_yaml.write_text(
        "buildings:\n"
        "  BuildingA: ['1:00-1:25']\n"
        "  BuildingB: ['1:15-1:40']\n"
        "movement:\n"
        "  policy: nonoverlap_time\n"
        "  travel_slots:\n"
        "    BuildingA:\n"
        "      BuildingA: 0\n"
        "      BuildingB: 1\n"
        "    BuildingB:\n"
        "      BuildingA: 1\n"
        "      BuildingB: 0\n"
    )
    with pytest.raises(ValueError, match="nonoverlap_time"):
        load_run_config(run_yaml)


def test_travel_time_allows_auto_travel_slots(tmp_path: Path):
    """travel_time policy should accept travel_slots: auto."""
    run_yaml = tmp_path / "run.yaml"
    run_yaml.write_text(
        "buildings:\n"
        "  BuildingA: ['1:00-1:25', '1:30-1:55']\n"
        "  BuildingB: ['1:15-1:40', '1:45-2:10']\n"
        "movement:\n"
        "  policy: travel_time\n"
        "  travel_slots: auto\n"
        "  min_buffer_minutes: 5\n"
    )
    cfg = load_run_config(run_yaml)
    assert cfg["movement"]["travel_slots"] == "auto"


def test_invalid_travel_slots_type_raises(tmp_path: Path):
    """travel_slots must be dict or 'auto' for travel-time policies."""
    run_yaml = tmp_path / "run.yaml"
    run_yaml.write_text(
        "buildings:\n"
        "  BuildingA: ['1:00-1:25']\n"
        "  BuildingB: ['1:15-1:40']\n"
        "movement:\n"
        "  policy: travel_time\n"
        "  travel_slots: 3\n"
    )
    with pytest.raises(ValueError, match="dictionary or 'auto'"):
        load_run_config(run_yaml)


def test_negative_min_buffer_minutes_raises(tmp_path: Path):
    """movement.min_buffer_minutes must be nonnegative."""
    run_yaml = tmp_path / "run.yaml"
    run_yaml.write_text(
        "buildings:\n"
        "  BuildingA: ['1:00-1:25']\n"
        "  BuildingB: ['1:15-1:40']\n"
        "movement:\n"
        "  policy: travel_time\n"
        "  travel_slots: auto\n"
        "  min_buffer_minutes: -1\n"
    )
    with pytest.raises(ValueError, match="min_buffer_minutes"):
        load_run_config(run_yaml)


def test_invalid_phase_slot_out_of_range_raises(tmp_path: Path):
    """Raise when phase slot is outside configured slot range."""
    run_yaml = tmp_path / "run.yaml"
    run_yaml.write_text(
        "buildings:\n"
        "  BuildingA: ['1:00-1:25', '1:30-1:55']\n"
        "movement:\n"
        "  policy: none\n"
        "  phase_slot:\n"
        "    BuildingA: 3\n"
    )
    with pytest.raises(ValueError, match="movement.phase_slot"):
        load_run_config(run_yaml)


def test_build_times_by_building_missing_buildings_raises():
    """Raise when building slot mapping is requested without buildings."""
    with pytest.raises(ValueError, match="building"):
        build_times_by_building({})


def test_invalid_faculty_building_raises(tmp_path: Path):
    """Raise when faculty entries reference unknown building names."""
    faculty_yaml = tmp_path / "faculty.yaml"
    faculty_yaml.write_text(
        "faculty:\n"
        "  Faculty A:\n"
        "    building: Unknown\n"
        "    room: '101'\n"
        "    areas: ['Area1']\n"
        "    status: active\n"
    )

    run_yaml = tmp_path / "run.yaml"
    run_yaml.write_text(
        "buildings:\n"
        "  BuildingA: ['1:00-1:25']\n"
        "  BuildingB: ['1:00-1:25']\n"
        "building_order: ['BuildingA', 'BuildingB']\n"
        "breaks: [1]\n"
    )

    csv_path = tmp_path / "visitors.csv"
    _write_csv(csv_path, [{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1"}])

    with pytest.raises(ValueError, match="building"):
        scheduler_from_configs(
            faculty_yaml,
            run_yaml,
            csv_path,
            mode=Mode.NO_OFFSET,
            solver=Solver.HIGHS,
        )


def test_gurobi_iis_missing_executable_raises(tmp_path: Path, monkeypatch):
    """Raise with a clear message when GUROBI_IIS executable path is invalid."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area1"}],
    )

    times_by_building = {"BuildingA": ["1:00-1:25"], "BuildingB": ["1:00-1:25"]}
    faculty_catalog = {
        "Faculty A": {
            "building": "BuildingA",
            "room": "101",
            "areas": ["Area1"],
            "status": "active",
        }
    }
    s = Scheduler(
        times_by_building=times_by_building,
        student_data_filename=str(csv_path),
        mode=Mode.BUILDING_A_FIRST,
        solver=Solver.GUROBI_IIS,
        faculty_catalog=faculty_catalog,
    )
    monkeypatch.setenv("GVS_GUROBI_IIS_EXECUTABLE", str(tmp_path / "missing_gurobi_ampl"))

    with pytest.raises(RuntimeError, match="GUROBI_IIS executable not found"):
        s.schedule_visitors(
            group_penalty=0.1,
            min_visitors=0,
            max_visitors=1,
            min_faculty=1,
            max_group=1,
            enforce_breaks=False,
            tee=False,
            run_name="test_iis_missing",
        )


def test_no_offset_without_breaks_raises(tmp_path: Path):
    """NO_OFFSET mode should require configured break times when building model."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area1"}],
    )
    times_by_building = {
        "BuildingA": ["1:00-1:25", "1:30-1:55"],
        "BuildingB": ["1:00-1:25", "1:30-1:55"],
    }
    faculty_catalog = {
        "Faculty A": {
            "building": "BuildingA",
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
    with pytest.raises(ValueError, match="Must specify some break times"):
        s.schedule_visitors(
            group_penalty=0.1,
            min_visitors=0,
            max_visitors=1,
            min_faculty=1,
            max_group=1,
            enforce_breaks=False,
            tee=False,
            run_name="no_breaks",
        )


def test_legacy_mode_no_offset_emits_futurewarning(tmp_path: Path):
    """Explicit use of legacy mode should emit FutureWarning."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area1"}],
    )
    times_by_building = {
        "BuildingA": ["1:00-1:25", "1:30-1:55"],
        "BuildingB": ["1:00-1:25", "1:30-1:55"],
    }
    faculty_catalog = {
        "Faculty A": {
            "building": "BuildingA",
            "room": "101",
            "areas": ["Area1"],
            "status": "active",
        }
    }
    with pytest.warns(FutureWarning, match="legacy interface"):
        Scheduler(
            times_by_building=times_by_building,
            student_data_filename=str(csv_path),
            mode=Mode.NO_OFFSET,
            solver=Solver.HIGHS,
            faculty_catalog=faculty_catalog,
        )


def test_mode_and_movement_together_emits_futurewarning(tmp_path: Path):
    """Providing both legacy mode and movement should warn and use movement."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area1"}],
    )
    times_by_building = {
        "BuildingA": ["1:00-1:25", "1:30-1:55"],
        "BuildingB": ["1:00-1:25", "1:30-1:55"],
    }
    faculty_catalog = {
        "Faculty A": {
            "building": "BuildingA",
            "room": "101",
            "areas": ["Area1"],
            "status": "active",
        }
    }
    with pytest.warns(FutureWarning, match="Ignoring `mode` and using `movement`"):
        s = Scheduler(
            times_by_building=times_by_building,
            student_data_filename=str(csv_path),
            mode=Mode.BUILDING_A_FIRST,
            movement={"policy": "none", "phase_slot": {"BuildingA": 1, "BuildingB": 1}},
            solver=Solver.HIGHS,
            faculty_catalog=faculty_catalog,
        )
    assert s.movement_policy == "none"


def test_no_offset_break_default_differs_from_movement_equivalent(tmp_path: Path):
    """Legacy NO_OFFSET implies breaks by default; movement-only does not."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area1"}],
    )
    times_by_building = {
        "BuildingA": ["1:00-1:25", "1:30-1:55"],
        "BuildingB": ["1:00-1:25", "1:30-1:55"],
    }
    faculty_catalog = {
        "Faculty A": {
            "building": "BuildingA",
            "room": "101",
            "areas": ["Area1"],
            "status": "active",
        }
    }

    with pytest.warns(FutureWarning, match="legacy interface"):
        s_mode = Scheduler(
            times_by_building=times_by_building,
            student_data_filename=str(csv_path),
            mode=Mode.NO_OFFSET,
            solver=Solver.HIGHS,
            faculty_catalog=faculty_catalog,
        )
    with pytest.raises(ValueError, match="Must specify some break times"):
        s_mode._build_model(
            group_penalty=0.1,
            min_visitors=0,
            max_visitors=1,
            min_faculty=1,
            max_group=1,
            enforce_breaks=False,
        )

    s_move = Scheduler(
        times_by_building=times_by_building,
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
        faculty_catalog=faculty_catalog,
    )
    s_move._build_model(
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=1,
        min_faculty=1,
        max_group=1,
        enforce_breaks=False,
    )
