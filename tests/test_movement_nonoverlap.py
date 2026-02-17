"""Additional hardening tests for shifted-clock movement behavior."""

from pathlib import Path

import pandas as pd
import pytest

from grad_visit_scheduler import Scheduler, Solver, compute_min_travel_lags
from grad_visit_scheduler.core import slot2min


def _write_csv(path: Path, rows):
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)


def _parse_times(times_by_building):
    return {b: [slot2min(slot) for slot in slots] for b, slots in times_by_building.items()}


def _has_real_time_overlap(solution):
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


def _build_slots(start_minute: int, duration: int, step: int, n_slots: int = 4):
    """Build deterministic slot labels from minute offsets."""
    slots = []
    for i in range(n_slots):
        start = start_minute + i * step
        end = start + duration
        slots.append(f"{start // 60}:{start % 60:02d}-{end // 60}:{end % 60:02d}")
    return slots


def test_compute_min_travel_lags_protects_all_overlapping_forward_transitions():
    """Any overlapping i->j cross-building transition should be blocked by derived lag."""
    times = {
        "A": ["1:00-1:20", "1:25-1:45", "1:50-2:10", "2:15-2:35"],
        "B": ["1:10-1:40", "1:45-2:15", "2:20-2:50", "2:55-3:25"],
        "C": ["1:05-1:25", "1:30-1:50", "1:55-2:15", "2:20-2:40"],
    }
    lags = compute_min_travel_lags(times, min_buffer_minutes=0)
    parsed = _parse_times(times)

    for b_from in times:
        for b_to in times:
            if b_from == b_to:
                continue
            lag = lags[b_from][b_to]
            for i, (_, end_from) in enumerate(parsed[b_from], start=1):
                for j, (start_to, _) in enumerate(parsed[b_to], start=1):
                    if j <= i:
                        continue
                    overlaps = start_to < end_from
                    if overlaps:
                        assert (j - i) <= lag


def test_compute_min_travel_lags_matrix_sweep_sufficiency():
    """Deterministic sweep over offsets/durations should always satisfy overlap blocking."""
    for offset_b in (0, 5, 10, 15, 20):
        for dur_a in (20, 25, 30):
            for dur_b in (20, 25, 30):
                for step_a in (25, 30):
                    for step_b in (25, 30):
                        times = {
                            "A": _build_slots(60, dur_a, step_a, n_slots=4),
                            "B": _build_slots(60 + offset_b, dur_b, step_b, n_slots=4),
                        }
                        lags = compute_min_travel_lags(times, min_buffer_minutes=0)
                        parsed = _parse_times(times)
                        for i, (_, end_from) in enumerate(parsed["A"], start=1):
                            for j, (start_to, _) in enumerate(parsed["B"], start=1):
                                if j <= i:
                                    continue
                                if start_to < end_from:
                                    assert (j - i) <= lags["A"]["B"]
                        for i, (_, end_from) in enumerate(parsed["B"], start=1):
                            for j, (start_to, _) in enumerate(parsed["A"], start=1):
                                if j <= i:
                                    continue
                                if start_to < end_from:
                                    assert (j - i) <= lags["B"]["A"]


def test_compute_min_travel_lags_is_minimal_when_positive():
    """For positive lag entries, reducing lag by one would allow an overlapping transition."""
    times = {
        "A": ["1:00-1:25", "1:30-1:55", "2:00-2:25", "2:30-2:55"],
        "B": ["1:15-2:05", "1:45-2:35", "2:15-3:05", "2:45-3:35"],
    }
    lags = compute_min_travel_lags(times)
    parsed = _parse_times(times)

    for b_from in times:
        for b_to in times:
            if b_from == b_to:
                continue
            lag = lags[b_from][b_to]
            if lag == 0:
                continue
            witness_found = False
            for i, (_, end_from) in enumerate(parsed[b_from], start=1):
                for j, (start_to, _) in enumerate(parsed[b_to], start=1):
                    if j - i != lag:
                        continue
                    if start_to < end_from:
                        witness_found = True
                        break
                if witness_found:
                    break
            assert witness_found


def test_compute_min_travel_lags_min_buffer_is_monotone():
    """Increasing min_buffer_minutes should never decrease any derived lag."""
    times = {
        "A": ["1:00-1:25", "1:30-1:55", "2:00-2:25", "2:30-2:55"],
        "B": ["1:15-1:40", "1:45-2:10", "2:15-2:40", "2:45-3:10"],
        "C": ["1:05-1:30", "1:35-2:00", "2:05-2:30", "2:35-3:00"],
    }
    lag0 = compute_min_travel_lags(times, min_buffer_minutes=0)
    lag10 = compute_min_travel_lags(times, min_buffer_minutes=10)
    for b_from in times:
        for b_to in times:
            assert lag10[b_from][b_to] >= lag0[b_from][b_to]


def test_compute_min_travel_lags_negative_buffer_raises():
    """Negative min_buffer_minutes should raise a clear ValueError."""
    times = {
        "A": ["1:00-1:25", "1:30-1:55"],
        "B": ["1:10-1:35", "1:40-2:05"],
    }
    with pytest.raises(ValueError, match="nonnegative"):
        compute_min_travel_lags(times, min_buffer_minutes=-1)


def test_compute_min_travel_lags_three_building_mixed_offsets_matrix():
    """Three-building mixed-offset deterministic sweep should produce valid lag matrices."""
    for offset_b in (0, 10, 20):
        for offset_c in (5, 15, 25):
            times = {
                "A": _build_slots(60, 25, 30, n_slots=4),
                "B": _build_slots(60 + offset_b, 25, 30, n_slots=4),
                "C": _build_slots(60 + offset_c, 25, 30, n_slots=4),
            }
            lags = compute_min_travel_lags(times, min_buffer_minutes=0)
            assert set(lags.keys()) == {"A", "B", "C"}
            for b_from in ("A", "B", "C"):
                for b_to in ("A", "B", "C"):
                    assert isinstance(lags[b_from][b_to], int)
                    assert lags[b_from][b_to] >= 0
                    if b_from == b_to:
                        assert lags[b_from][b_to] == 0


def test_nonoverlap_policy_matches_travel_time_auto_lag_matrix(tmp_path: Path):
    """nonoverlap_time and travel_time+auto should derive identical lag matrices."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [{"Name": "Visitor 1", "Prof1": "Faculty A", "Prof2": "Faculty B", "Area1": "Area1", "Area2": "Area2"}],
    )

    times = {
        "BuildingA": ["1:00-1:25", "1:30-1:55", "2:00-2:25", "2:30-2:55"],
        "BuildingB": ["1:15-1:40", "1:45-2:10", "2:15-2:40", "2:45-3:10"],
    }
    faculty_catalog = {
        "Faculty A": {"building": "BuildingA", "room": "101", "areas": ["Area1"], "status": "active"},
        "Faculty B": {"building": "BuildingB", "room": "201", "areas": ["Area2"], "status": "active"},
    }

    s_nonoverlap = Scheduler(
        times_by_building=times,
        student_data_filename=str(csv_path),
        movement={"policy": "nonoverlap_time", "phase_slot": {"BuildingA": 1, "BuildingB": 1}},
        solver=Solver.HIGHS,
        faculty_catalog=faculty_catalog,
    )
    s_auto = Scheduler(
        times_by_building=times,
        student_data_filename=str(csv_path),
        movement={
            "policy": "travel_time",
            "phase_slot": {"BuildingA": 1, "BuildingB": 1},
            "travel_slots": "auto",
        },
        solver=Solver.HIGHS,
        faculty_catalog=faculty_catalog,
    )

    assert s_nonoverlap.travel_slots == s_auto.travel_slots


def test_three_building_shifted_none_can_feasible_overlap_while_nonoverlap_blocks(tmp_path: Path):
    """3-building shifted case can be feasible under none but infeasible under nonoverlap_time."""
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [{"Name": "Visitor 1", "Prof1": "Prof B", "Prof2": "Prof A", "Prof3": "Prof C", "Area1": "Area1", "Area2": "Area2"}],
    )
    times = {
        "A": ["1:00-1:25", "1:30-1:55", "2:00-2:25", "2:30-2:55"],
        "B": ["1:10-1:35", "1:40-2:05", "2:10-2:35", "2:40-3:05"],
        "C": ["1:50-2:15", "2:20-2:45", "2:50-3:15", "3:20-3:45"],
    }
    faculty_catalog = {
        "Prof A": {"building": "A", "room": "101", "areas": ["Area1"], "status": "active"},
        "Prof B": {"building": "B", "room": "201", "areas": ["Area1"], "status": "active"},
        "Prof C": {"building": "C", "room": "301", "areas": ["Area2"], "status": "active"},
    }

    movement_none = {"policy": "none", "phase_slot": {"A": 1, "B": 1, "C": 1}}
    movement_nonoverlap = {"policy": "nonoverlap_time", "phase_slot": {"A": 1, "B": 1, "C": 1}}

    with pytest.warns(UserWarning, match="real-time visitor overlaps"):
        s_none = Scheduler(
            times_by_building=times,
            student_data_filename=str(csv_path),
            movement=movement_none,
            solver=Solver.HIGHS,
            faculty_catalog=faculty_catalog,
        )
    s_none.faculty_limited_availability("Prof B", [2])
    s_none.faculty_limited_availability("Prof A", [3])
    s_none.faculty_limited_availability("Prof C", [4])
    sol_none = s_none.schedule_visitors(
        group_penalty=0.0,
        min_visitors=0,
        max_visitors=2,
        min_faculty=3,
        max_group=1,
        enforce_breaks=False,
        tee=False,
    )
    assert sol_none is not None
    assert _has_real_time_overlap(sol_none)

    s_nonoverlap = Scheduler(
        times_by_building=times,
        student_data_filename=str(csv_path),
        movement=movement_nonoverlap,
        solver=Solver.HIGHS,
        faculty_catalog=faculty_catalog,
    )
    s_nonoverlap.faculty_limited_availability("Prof B", [2])
    s_nonoverlap.faculty_limited_availability("Prof A", [3])
    s_nonoverlap.faculty_limited_availability("Prof C", [4])
    sol_nonoverlap = s_nonoverlap.schedule_visitors(
        group_penalty=0.0,
        min_visitors=0,
        max_visitors=2,
        min_faculty=3,
        max_group=1,
        enforce_breaks=False,
        tee=False,
    )
    assert sol_nonoverlap is None
