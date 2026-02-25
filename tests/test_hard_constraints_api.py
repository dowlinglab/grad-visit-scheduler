"""Tests for visitor-specific hard-constraint APIs on Scheduler."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import grad_visit_scheduler.core as core_mod
from grad_visit_scheduler import Mode, Scheduler, Solver


def _write_csv(path: Path, rows):
    pd.DataFrame(rows).to_csv(path, index=False)


def _highs_available() -> bool:
    try:
        return core_mod.pyo.SolverFactory("appsi_highs").available() or core_mod.pyo.SolverFactory("highs").available()
    except Exception:
        return False


def _build_scheduler(tmp_path: Path) -> Scheduler:
    csv_path = tmp_path / "visitors.csv"
    _write_csv(
        csv_path,
        [
            {"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area2"},
            {"Name": "Visitor 2", "Prof1": "Faculty B", "Area1": "Area1", "Area2": "Area2"},
        ],
    )
    times_by_building = {
        "BuildingA": ["1:00-1:25", "1:30-1:55"],
        "BuildingB": ["1:00-1:25", "1:30-1:55"],
    }
    faculty_catalog = {
        "Faculty A": {"building": "BuildingA", "room": "101", "areas": ["Area1"], "status": "active"},
        "Faculty B": {"building": "BuildingA", "room": "102", "areas": ["Area2"], "status": "active"},
    }
    return Scheduler(
        times_by_building=times_by_building,
        student_data_filename=str(csv_path),
        mode=Mode.BUILDING_A_FIRST,
        solver=Solver.HIGHS,
        faculty_catalog=faculty_catalog,
    )


def test_forbid_require_break_basic_and_idempotent_storage(tmp_path: Path):
    """APIs should accept valid calls and remain idempotent for duplicate rules."""
    s = _build_scheduler(tmp_path)

    s.forbid_meeting("Visitor 1", "Faculty A")
    s.forbid_meeting("Visitor 1", "Faculty A")  # duplicate
    s.forbid_meeting("Visitor 1", "Faculty B", time_slot=2)
    s.forbid_meeting("Visitor 1", "Faculty B", time_slot=2)  # duplicate

    s.require_meeting("Visitor 2", "Faculty B")
    s.require_meeting("Visitor 2", "Faculty B")  # duplicate
    s.require_meeting("Visitor 2", "Faculty A", time_slot=1)
    s.require_meeting("Visitor 2", "Faculty A", time_slot=1)  # duplicate

    s.require_break("Visitor 1", slots=[1, 2], min_breaks=1)
    s.require_break("Visitor 1", slots=[2, 1], min_breaks=1)  # duplicate after normalization

    assert len(s._forbidden_meetings_all_slots) == 1
    assert len(s._forbidden_meetings_by_slot) == 1
    assert len(s._required_meetings_all_slots) == 1
    assert len(s._required_meetings_by_slot) == 1
    assert len(s._required_breaks) == 1


def test_invalid_inputs_raise_clear_value_error(tmp_path: Path):
    """Unknown names and invalid slots/min_breaks should raise ValueError."""
    s = _build_scheduler(tmp_path)

    with pytest.raises(ValueError, match="Unknown visitor"):
        s.forbid_meeting("No Visitor", "Faculty A")
    with pytest.raises(ValueError, match="Unknown faculty"):
        s.forbid_meeting("Visitor 1", "No Faculty")
    with pytest.raises(ValueError, match="Invalid time_slot"):
        s.forbid_meeting("Visitor 1", "Faculty A", time_slot=3)
    with pytest.raises(ValueError, match="Invalid time_slot"):
        s.forbid_meeting("Visitor 1", "Faculty A", time_slot="not_an_int")

    with pytest.raises(ValueError, match="Unknown visitor"):
        s.require_break("No Visitor", slots=[1], min_breaks=1)
    with pytest.raises(ValueError, match="slots must be an iterable"):
        s.require_break("Visitor 1", slots="1,2", min_breaks=1)
    with pytest.raises(ValueError, match="slots must contain at least one"):
        s.require_break("Visitor 1", slots=[], min_breaks=1)
    with pytest.raises(ValueError, match="min_breaks must be an integer"):
        s.require_break("Visitor 1", slots=[1], min_breaks="one")
    with pytest.raises(ValueError, match="min_breaks must be nonnegative"):
        s.require_break("Visitor 1", slots=[1], min_breaks=-1)
    with pytest.raises(ValueError, match="larger than the number of provided slots"):
        s.require_break("Visitor 1", slots=[1], min_breaks=2)


def test_contradictory_constraints_raise_helpful_errors(tmp_path: Path):
    """Directly contradictory user hard constraints should fail early."""
    s = _build_scheduler(tmp_path)
    s.require_meeting("Visitor 1", "Faculty A", time_slot=1)
    with pytest.raises(ValueError, match="Contradictory hard constraints"):
        s.forbid_meeting("Visitor 1", "Faculty A", time_slot=1)

    s2 = _build_scheduler(tmp_path)
    s2.forbid_meeting("Visitor 1", "Faculty A")
    with pytest.raises(ValueError, match="Contradictory hard constraints"):
        s2.require_meeting("Visitor 1", "Faculty A")

    s3 = _build_scheduler(tmp_path)
    s3.require_meeting("Visitor 1", "Faculty A", time_slot=1)
    with pytest.raises(ValueError, match="require_break allows at most"):
        s3.require_break("Visitor 1", slots=[1], min_breaks=1)


def test_require_meeting_respects_availability_early(tmp_path: Path):
    """Require-meeting should fail early when slot is unavailable."""
    s = _build_scheduler(tmp_path)
    s.specify_limited_student_availability({"Visitor 1": [2], "Visitor 2": [1, 2]})
    with pytest.raises(ValueError, match="outside faculty or visitor availability"):
        s.require_meeting("Visitor 1", "Faculty A", time_slot=1)


def test_require_meeting_no_slot_form_error_paths(tmp_path: Path):
    """Non-slot require-meeting should raise for no-feasible and all-forbidden cases."""
    s = _build_scheduler(tmp_path)
    s.specify_limited_student_availability({"Visitor 1": [1, 2], "Visitor 2": [1, 2]})
    s.faculty_limited_availability("Faculty A", [])
    with pytest.raises(ValueError, match="no feasible slot remains"):
        s.require_meeting("Visitor 1", "Faculty A")

    s2 = _build_scheduler(tmp_path)
    s2.specify_limited_student_availability({"Visitor 1": [1, 2], "Visitor 2": [1, 2]})
    s2.forbid_meeting("Visitor 1", "Faculty A", time_slot=1)
    s2.forbid_meeting("Visitor 1", "Faculty A", time_slot=2)
    with pytest.raises(ValueError, match="all feasible slots"):
        s2.require_meeting("Visitor 1", "Faculty A")


def test_integration_solve_enforces_hard_constraints(tmp_path: Path):
    """Solved schedule should satisfy all added hard constraints."""
    if not _highs_available():
        pytest.skip("HiGHS backend is not available")

    s = _build_scheduler(tmp_path)
    s.require_meeting("Visitor 1", "Faculty A", time_slot=1)
    s.forbid_meeting("Visitor 1", "Faculty B")
    s.require_break("Visitor 1", slots=[1, 2], min_breaks=1)
    s.require_meeting("Visitor 2", "Faculty B")  # non-slot-specific form
    s.forbid_meeting("Visitor 2", "Faculty A", time_slot=2)  # slot-specific forbid

    sol = s.schedule_visitors(
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=4,
        min_faculty=0,
        max_group=1,
        enforce_breaks=False,
        tee=False,
        run_name="hard_constraints_integration",
    )
    assert sol is not None

    assert sol.meeting_assigned("Visitor 1", "Faculty A", 1)
    assert not any(sol.meeting_assigned("Visitor 1", "Faculty B", t) for t in (1, 2))
    assert sum(
        1
        for f in sol.faculty
        for t in (1, 2)
        if sol.meeting_assigned("Visitor 1", f, t)
    ) <= 1

    assert sum(1 for t in sol.time_slots if sol.meeting_assigned("Visitor 2", "Faculty B", t)) == 1
    assert not sol.meeting_assigned("Visitor 2", "Faculty A", 2)
