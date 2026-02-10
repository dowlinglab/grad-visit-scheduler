from pathlib import Path

from grad_visit_scheduler import scheduler_from_configs, Mode, Solver
from grad_visit_scheduler.config import load_faculty_catalog, load_run_config


def test_load_faculty_catalog():
    faculty, aliases = load_faculty_catalog(
        Path(__file__).parents[1] / "examples" / "faculty_example.yaml"
    )
    assert "Faculty A" in faculty
    assert aliases.get("Faculty Bee") == "Faculty B"


def test_load_run_config():
    run_cfg = load_run_config(Path(__file__).parents[1] / "examples" / "config_basic.yaml")
    assert "buildings" in run_cfg
    assert "faculty_availability" in run_cfg


def test_scheduler_from_configs():
    root = Path(__file__).parents[1]
    s = scheduler_from_configs(
        root / "examples" / "faculty_example.yaml",
        root / "examples" / "config_basic.yaml",
        root / "examples" / "data_fake_visitors.csv",
        mode=Mode.NO_OFFSET,
        solver=Solver.HIGHS,
    )
    assert s.number_time_slots == 4
    assert "Faculty A" in s.faculty
    assert s.faculty["Faculty D"]["avail"] == []
