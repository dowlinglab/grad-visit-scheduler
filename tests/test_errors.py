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


def test_invalid_building_order_shape_raises(tmp_path: Path):
    """Raise when building_order is not a list of exactly two names."""
    run_yaml = tmp_path / "run.yaml"
    run_yaml.write_text(
        "buildings:\n"
        "  BuildingA: ['1:00-1:25']\n"
        "  BuildingB: ['1:00-1:25']\n"
        "building_order: ['BuildingA']\n"
    )
    with pytest.raises(ValueError, match="exactly two"):
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
