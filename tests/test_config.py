"""Configuration loader tests."""

from pathlib import Path

from grad_visit_scheduler import scheduler_from_configs, Solver
from grad_visit_scheduler.core import slot2min
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


def test_shifted_nonoverlap_example_solves_without_real_time_overlap():
    """Dedicated shifted-clock nonoverlap example should solve without overlap."""
    root = Path(__file__).parents[1]
    s = scheduler_from_configs(
        root / "examples" / "faculty_example.yaml",
        root / "examples" / "config_shifted_nonoverlap_auto.yaml",
        root / "examples" / "data_fake_visitors.csv",
        solver=Solver.HIGHS,
    )
    sol = s.schedule_visitors(
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=4,
        min_faculty=1,
        max_group=2,
        enforce_breaks=False,
        tee=False,
        run_name="shifted_nonoverlap_example",
    )
    assert sol is not None
    assert s.movement_policy == "nonoverlap_time"
    assert not _has_real_time_overlap(sol)
