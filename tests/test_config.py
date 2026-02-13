"""Configuration loader tests."""

from pathlib import Path

from grad_visit_scheduler import scheduler_from_configs, Solver
from grad_visit_scheduler.config import load_faculty_catalog, load_run_config


def test_load_faculty_catalog():
    """Verify faculty catalog parsing and alias loading."""
    faculty, aliases = load_faculty_catalog(
        Path(__file__).parents[1] / "examples" / "faculty_example.yaml"
    )
    assert "Faculty A" in faculty
    assert aliases.get("Faculty Bee") == "Faculty B"
    assert faculty["Faculty C"]["status"] == "legacy"
    assert faculty["Faculty D"]["status"] == "external"


def test_load_run_config():
    """Verify run config parsing for expected keys."""
    run_cfg = load_run_config(Path(__file__).parents[1] / "examples" / "config_basic.yaml")
    assert "buildings" in run_cfg
    assert "faculty_availability" in run_cfg
    assert run_cfg["building_order"] == ["BuildingA", "BuildingB"]
    assert run_cfg["movement"]["policy"] == "none"
    assert run_cfg["breaks"] == [2]


def test_scheduler_from_configs():
    """Verify scheduler creation from config files."""
    root = Path(__file__).parents[1]
    s = scheduler_from_configs(
        root / "examples" / "faculty_example.yaml",
        root / "examples" / "config_basic.yaml",
        root / "examples" / "data_fake_visitors.csv",
        solver=Solver.HIGHS,
    )
    assert s.number_time_slots == 4
    assert "Faculty A" in s.faculty
    assert s.faculty["Faculty D"]["avail"] == []
    assert s.building_a == "BuildingA"
    assert s.building_b == "BuildingB"
    assert s.break_times == [2]
    assert s.faculty["Faculty B"]["avail"] == [1, 2, 3, 4]
    assert s.movement_policy == "none"
