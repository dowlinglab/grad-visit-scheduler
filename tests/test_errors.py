from pathlib import Path
import pytest
import pandas as pd

from grad_visit_scheduler import Scheduler, Mode, Solver, scheduler_from_configs
from grad_visit_scheduler.config import load_faculty_catalog, load_run_config, build_times_by_building


def _write_csv(path: Path, rows):
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)


def test_missing_name_column_raises(tmp_path: Path):
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
    faculty_yaml = tmp_path / "faculty.yaml"
    faculty_yaml.write_text(
        "faculty:\n  Faculty A:\n    building: BuildingB\n    room: '101'\n    areas: ['Area1']\n    status: active\naliases:\n  Alias A: Faculty B\n"
    )

    with pytest.raises(ValueError, match="Alias target"):
        load_faculty_catalog(faculty_yaml)


def test_missing_buildings_in_run_config_raises(tmp_path: Path):
    run_yaml = tmp_path / "run.yaml"
    run_yaml.write_text("breaks: [1]\n")

    with pytest.raises(ValueError, match="buildings"):
        load_run_config(run_yaml)


def test_build_times_by_building_missing_buildings_raises():
    with pytest.raises(ValueError, match="building"):
        build_times_by_building({})


def test_invalid_faculty_building_raises(tmp_path: Path):
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
