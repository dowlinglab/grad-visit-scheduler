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


def _build_break_scheduler(
    tmp_path: Path,
    *,
    visitor_rows: list[dict] | None = None,
    slots: list[str] | None = None,
    breaks: list[int] | None = None,
    faculty_available: list[int] | None = None,
) -> Scheduler:
    """Build a small one-building scheduler for faculty-break tests."""
    csv_path = tmp_path / "visitors_breaks.csv"
    if visitor_rows is None:
        visitor_rows = [{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area1"}]
    _write_csv(csv_path, visitor_rows)

    if slots is None:
        slots = ["8:30 AM-8:55 AM", "9:00 AM-9:25 AM", "9:30 AM-9:55 AM"]
    times_by_building = {"Zoom": slots}
    if breaks is not None:
        times_by_building["breaks"] = breaks
    if faculty_available is None:
        faculty_available = list(range(1, len(slots) + 1))
    faculty_catalog = {
        "Faculty A": {"building": "Zoom", "room": "Zoom", "areas": ["Area1"], "status": "active"},
    }
    scheduler = Scheduler(
        times_by_building=times_by_building,
        student_data_filename=str(csv_path),
        movement={"policy": "none", "phase_slot": {"Zoom": 1}},
        solver=Solver.HIGHS,
        faculty_catalog=faculty_catalog,
    )
    scheduler.faculty_limited_availability("Faculty A", faculty_available)
    return scheduler


def _build_five_slot_virtual_scheduler(tmp_path: Path) -> Scheduler:
    """Build a five-slot one-building scheduler for break-semantic regression tests."""
    csv_path = tmp_path / "visitors_five_slot.csv"
    _write_csv(
        csv_path,
        [
            {
                "Name": "Visitor 1",
                "Prof1": "Faculty A",
                "Prof2": "Faculty B",
                "Prof3": "Faculty C",
                "Prof4": "Faculty D",
                "Prof5": "Faculty E",
                "Area1": "Area1",
                "Area2": "Area1",
            }
        ],
    )
    times_by_building = {
        "Zoom": [
            "8:30 AM-8:55 AM",
            "9:00 AM-9:25 AM",
            "9:30 AM-9:55 AM",
            "10:00 AM-10:25 AM",
            "10:30 AM-10:55 AM",
        ],
        "breaks": [1, 2, 3, 4, 5],
    }
    faculty_catalog = {
        name: {"building": "Zoom", "room": "Zoom", "areas": ["Area1"], "status": "active"}
        for name in ["Faculty A", "Faculty B", "Faculty C", "Faculty D", "Faculty E"]
    }
    return Scheduler(
        times_by_building=times_by_building,
        student_data_filename=str(csv_path),
        movement={"policy": "none", "phase_slot": {"Zoom": 1}},
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


def test_enforce_breaks_false_disables_automatic_faculty_break_vars(tmp_path: Path):
    """False should preserve the no-automatic-break behavior."""
    s = _build_break_scheduler(tmp_path, breaks=[1, 2, 3])
    s._build_model(
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=1,
        min_faculty=0,
        max_group=1,
        enforce_breaks=False,
    )
    assert not hasattr(s.model, "faculty_breaks")


@pytest.mark.skipif(not _highs_available(), reason="HiGHS solver unavailable")
@pytest.mark.parametrize(
    ("kwargs", "expected_warning"),
    [
        ({"enforce_breaks": True}, None),
        ({"faculty_breaks": 1}, None),
        ({"enforce_breaks": True, "faculty_breaks": 1}, "Ignoring `enforce_breaks`"),
    ],
)
def test_boolean_alias_and_explicit_faculty_breaks_require_one_break(tmp_path: Path, kwargs, expected_warning):
    """Legacy alias and explicit faculty break counts should both support one faculty break."""
    s = _build_break_scheduler(tmp_path, breaks=[1, 2])
    solve_kwargs = dict(
        group_penalty=0.1,
        min_visitors=1,
        max_visitors=1,
        min_faculty=1,
        max_group=1,
        tee=False,
        run_name="break_one",
    )
    solve_kwargs.update(kwargs)
    if expected_warning is None:
        sol = s.schedule_visitors(**solve_kwargs)
    else:
        with pytest.warns(FutureWarning, match=expected_warning):
            sol = s.schedule_visitors(**solve_kwargs)
    assert sol is not None
    count = sum(round(core_mod.pyo.value(s.model.faculty_breaks["Faculty A", t])) for t in s.model.break_options)
    assert count == 1


@pytest.mark.skipif(not _highs_available(), reason="HiGHS solver unavailable")
def test_faculty_breaks_integer_two_requires_two_faculty_breaks(tmp_path: Path):
    """A positive faculty break count should require that many faculty breaks."""
    s = _build_break_scheduler(tmp_path, breaks=[1, 2, 3])
    sol = s.schedule_visitors(
        group_penalty=0.1,
        min_visitors=1,
        max_visitors=1,
        min_faculty=1,
        max_group=1,
        faculty_breaks=2,
        tee=False,
        run_name="break_two",
    )
    assert sol is not None
    count = sum(round(core_mod.pyo.value(s.model.faculty_breaks["Faculty A", t])) for t in s.model.break_options)
    assert count == 2


@pytest.mark.skipif(not _highs_available(), reason="HiGHS solver unavailable")
def test_unavailable_faculty_slots_count_toward_requested_breaks(tmp_path: Path):
    """Limited-availability slots outside the break window should count as breaks."""
    s = _build_break_scheduler(
        tmp_path,
        slots=["8:30 AM-8:55 AM", "9:00 AM-9:25 AM", "9:30 AM-9:55 AM"],
        breaks=[1, 2],
        faculty_available=[1, 2],
    )
    sol = s.schedule_visitors(
        group_penalty=0.1,
        min_visitors=1,
        max_visitors=1,
        min_faculty=1,
        max_group=1,
        faculty_breaks=2,
        tee=False,
        run_name="break_unavailable_counts",
    )
    assert sol is not None
    count = sum(round(core_mod.pyo.value(s.model.faculty_breaks["Faculty A", t])) for t in s.model.break_options)
    assert count == 1


def test_invalid_break_values_raise_clear_errors(tmp_path: Path):
    """Negative and non-integer break counts should be rejected."""
    s = _build_break_scheduler(tmp_path, breaks=[1, 2, 3])
    for field in ("faculty_breaks", "student_breaks"):
        for bad in (-1, "two", 1.5):
            with pytest.raises(ValueError, match=field):
                s._build_model(
                    group_penalty=0.1,
                    min_visitors=0,
                    max_visitors=1,
                    min_faculty=0,
                    max_group=1,
                    **{field: bad},
                )
    for bad in (1, "two"):
        with pytest.raises(ValueError, match="enforce_breaks"):
            s._build_model(
                group_penalty=0.1,
                min_visitors=0,
                max_visitors=1,
                min_faculty=0,
                max_group=1,
                enforce_breaks=bad,
            )


def test_break_counts_reject_impossible_requests(tmp_path: Path):
    """Requested break counts above the break capacity should fail early."""
    s = _build_break_scheduler(tmp_path, breaks=[2], faculty_available=[1, 2, 3])
    with pytest.raises(ValueError, match="maximum possible faculty breaks"):
        s._build_model(
            group_penalty=0.1,
            min_visitors=0,
            max_visitors=1,
            min_faculty=0,
            max_group=1,
            faculty_breaks=2,
        )
    with pytest.raises(ValueError, match="student_breaks=2"):
        s._build_model(
            group_penalty=0.1,
            min_visitors=0,
            max_visitors=1,
            min_faculty=0,
            max_group=1,
            student_breaks=2,
        )


@pytest.mark.skipif(not _highs_available(), reason="HiGHS solver unavailable")
def test_faculty_breaks_can_make_schedule_infeasible(tmp_path: Path):
    """A feasible faculty break count can still make the solve infeasible once meeting bounds apply."""
    s = _build_break_scheduler(
        tmp_path,
        visitor_rows=[
            {"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area1"},
            {"Name": "Visitor 2", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area1"},
        ],
        breaks=[1, 2, 3],
    )
    sol = s.schedule_visitors(
        group_penalty=0.1,
        min_visitors=2,
        max_visitors=2,
        min_faculty=0,
        max_group=1,
        faculty_breaks=2,
        tee=False,
        run_name="break_infeasible",
    )
    assert sol is None


@pytest.mark.skipif(not _highs_available(), reason="HiGHS solver unavailable")
def test_schedule_visitors_top_n_accepts_break_count_args(tmp_path: Path):
    """Top-N solve path should accept the explicit break-count interface."""
    s = _build_break_scheduler(tmp_path, breaks=[1, 2, 3])
    top = s.schedule_visitors_top_n(
        n_solutions=1,
        group_penalty=0.1,
        min_visitors=1,
        max_visitors=1,
        min_faculty=1,
        max_group=1,
        faculty_breaks=2,
        tee=False,
        run_name="break_top_n",
    )
    assert len(top) == 1


@pytest.mark.skipif(not _highs_available(), reason="HiGHS solver unavailable")
def test_explicit_faculty_breaks_do_not_impose_automatic_student_breaks(tmp_path: Path):
    """Explicit faculty breaks should not inherit the legacy student-break toggle."""
    s_false = _build_five_slot_virtual_scheduler(tmp_path)
    sol_false = s_false.schedule_visitors(
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=8,
        min_faculty=5,
        max_group=3,
        enforce_breaks=False,
        tee=False,
        run_name="five_slot_false",
    )
    assert sol_false is not None

    s_int = _build_five_slot_virtual_scheduler(tmp_path)
    sol_int = s_int.schedule_visitors(
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=8,
        min_faculty=5,
        max_group=3,
        faculty_breaks=1,
        tee=False,
        run_name="five_slot_int",
    )
    assert sol_int is not None

    s_true = _build_five_slot_virtual_scheduler(tmp_path)
    sol_true = s_true.schedule_visitors(
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=8,
        min_faculty=5,
        max_group=3,
        enforce_breaks=True,
        tee=False,
        run_name="five_slot_true",
    )
    assert sol_true is None


@pytest.mark.skipif(not _highs_available(), reason="HiGHS solver unavailable")
def test_student_breaks_accept_integer_counts(tmp_path: Path):
    """Student break counts should support integers greater than one."""
    s = _build_break_scheduler(
        tmp_path,
        breaks=[1, 2, 3],
        visitor_rows=[{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area1"}],
    )
    sol = s.schedule_visitors(
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=1,
        min_faculty=0,
        max_group=1,
        student_breaks=2,
        tee=False,
        run_name="student_breaks_two",
    )
    assert sol is not None
    meetings_in_break_window = sum(
        round(core_mod.pyo.value(s.model.y["Visitor 1", "Faculty A", t])) for t in s.model.break_options
    )
    assert meetings_in_break_window <= 1


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


def test_optional_bounds_api_validation_and_clear(tmp_path: Path):
    """Optional bounds APIs should validate values and support clearing with None."""
    s = _build_scheduler(tmp_path)

    with pytest.raises(ValueError, match="Unknown visitor"):
        s.set_visitor_meeting_bounds("No Visitor", min_meetings=1)
    with pytest.raises(ValueError, match="Unknown faculty"):
        s.set_faculty_meeting_bounds("No Faculty", min_meetings=1)
    with pytest.raises(ValueError, match="nonnegative integer or None"):
        s.set_visitor_meeting_bounds("Visitor 1", min_meetings="bad")
    with pytest.raises(ValueError, match="nonnegative integer or None"):
        s.set_faculty_meeting_bounds("Faculty A", max_meetings=-1)
    with pytest.raises(ValueError, match="exceeds"):
        s.set_visitor_meeting_bounds("Visitor 1", min_meetings=2, max_meetings=1)
    with pytest.raises(ValueError, match="exceeds"):
        s.set_faculty_meeting_bounds("Faculty A", min_meetings=3, max_meetings=2)

    s.set_visitor_meeting_bounds("Visitor 1", min_meetings=1, max_meetings=1)
    s.set_faculty_meeting_bounds("Faculty A", min_meetings=1, max_meetings=1)
    assert "Visitor 1" in s._visitor_meeting_bounds
    assert "Faculty A" in s._faculty_meeting_bounds

    s.set_visitor_meeting_bounds("Visitor 1", min_meetings=None, max_meetings=None)
    s.set_faculty_meeting_bounds("Faculty A", min_meetings=None, max_meetings=None)
    assert "Visitor 1" not in s._visitor_meeting_bounds
    assert "Faculty A" not in s._faculty_meeting_bounds


def test_presolve_checks_raise_with_api_recommendations(tmp_path: Path):
    """Pre-solve checks should fail early and recommend optional bound APIs."""
    s = _build_scheduler(tmp_path)
    s.require_meeting("Visitor 1", "Faculty A")
    s.set_visitor_meeting_bounds("Visitor 1", max_meetings=0)
    with pytest.raises(ValueError, match="set_visitor_meeting_bounds"):
        s.schedule_visitors(
            group_penalty=0.1,
            min_visitors=0,
            max_visitors=4,
            min_faculty=0,
            max_group=1,
            enforce_breaks=False,
            tee=False,
            run_name="presolve_visitor_bounds",
        )

    s2 = _build_scheduler(tmp_path)
    s2.require_meeting("Visitor 1", "Faculty A")
    s2.require_meeting("Visitor 2", "Faculty A")
    s2.set_faculty_meeting_bounds("Faculty A", max_meetings=1)
    with pytest.raises(ValueError, match="set_faculty_meeting_bounds"):
        s2.schedule_visitors(
            group_penalty=0.1,
            min_visitors=0,
            max_visitors=4,
            min_faculty=0,
            max_group=1,
            enforce_breaks=False,
            tee=False,
            run_name="presolve_faculty_bounds",
        )


def test_presolve_default_fast_fail_happens_before_model_build(tmp_path: Path, monkeypatch):
    """Default pre-check mode should fail before attempting model construction."""
    s = _build_scheduler(tmp_path)
    s.require_meeting("Visitor 1", "Faculty A")
    s.set_visitor_meeting_bounds("Visitor 1", max_meetings=0)

    called = {"build": 0}
    original_build = s._build_model

    def _wrapped_build(*args, **kwargs):
        called["build"] += 1
        return original_build(*args, **kwargs)

    monkeypatch.setattr(s, "_build_model", _wrapped_build)

    with pytest.raises(ValueError, match="Pre-solve hard-constraint checks found contradictions"):
        s.schedule_visitors(
            group_penalty=0.1,
            min_visitors=0,
            max_visitors=4,
            min_faculty=0,
            max_group=1,
            enforce_breaks=False,
            debug_infeasible=False,
            tee=False,
            run_name="fast_fail_before_build",
        )
    assert called["build"] == 0


def test_presolve_debug_mode_builds_model_then_raises(tmp_path: Path):
    """debug_infeasible=True should build model first, then raise on checks."""
    s = _build_scheduler(tmp_path)
    s.require_meeting("Visitor 1", "Faculty A")
    s.set_visitor_meeting_bounds("Visitor 1", max_meetings=0)

    with pytest.raises(ValueError, match="Pre-solve hard-constraint checks found contradictions"):
        s.schedule_visitors(
            group_penalty=0.1,
            min_visitors=0,
            max_visitors=4,
            min_faculty=0,
            max_group=1,
            enforce_breaks=False,
            debug_infeasible=True,
            tee=False,
            run_name="debug_build_then_raise",
        )
    assert hasattr(s, "model")
    assert hasattr(s.model, "y")


def test_collect_wrapper_can_return_issues_without_raising(tmp_path: Path):
    """Wrapper should support collect-only mode for debug workflows."""
    s = _build_scheduler(tmp_path)
    s.require_meeting("Visitor 1", "Faculty A")
    s.set_visitor_meeting_bounds("Visitor 1", max_meetings=0)
    issues = s._run_presolve_hard_constraint_checks(
        min_visitors=0,
        max_visitors=4,
        min_faculty=0,
        max_group=1,
        raise_on_issue=False,
    )
    assert len(issues) >= 1
    assert any("set_visitor_meeting_bounds" in msg for msg in issues)


def test_top_n_debug_infeasible_builds_then_raises(tmp_path: Path):
    """Top-N API should support debug_infeasible behavior consistently."""
    s = _build_scheduler(tmp_path)
    s.require_meeting("Visitor 1", "Faculty A")
    s.set_visitor_meeting_bounds("Visitor 1", max_meetings=0)
    with pytest.raises(ValueError, match="Pre-solve hard-constraint checks found contradictions"):
        s.schedule_visitors_top_n(
            n_solutions=2,
            group_penalty=0.1,
            min_visitors=0,
            max_visitors=4,
            min_faculty=0,
            max_group=1,
            enforce_breaks=False,
            debug_infeasible=True,
            tee=False,
            run_name="topn_debug_raise",
        )
    assert hasattr(s, "model")
    assert hasattr(s.model, "y")


def test_presolve_checks_for_slot_collisions(tmp_path: Path):
    """Pre-solve should reject obvious fixed-slot collisions before MILP solve."""
    s = _build_scheduler(tmp_path)
    s.require_meeting("Visitor 1", "Faculty A", time_slot=1)
    s.require_meeting("Visitor 1", "Faculty B", time_slot=1)
    with pytest.raises(ValueError, match="No-simultaneous-meeting constraint"):
        s.schedule_visitors(
            group_penalty=0.1,
            min_visitors=0,
            max_visitors=4,
            min_faculty=0,
            max_group=1,
            enforce_breaks=False,
            tee=False,
            run_name="presolve_visitor_slot_collision",
        )

    s2 = _build_scheduler(tmp_path)
    s2.require_meeting("Visitor 1", "Faculty A", time_slot=1)
    s2.require_meeting("Visitor 2", "Faculty A", time_slot=1)
    with pytest.raises(ValueError, match="exceeds max_group"):
        s2.schedule_visitors(
            group_penalty=0.1,
            min_visitors=0,
            max_visitors=4,
            min_faculty=0,
            max_group=1,
            enforce_breaks=False,
            tee=False,
            run_name="presolve_faculty_slot_collision",
        )


def test_optional_bounds_are_enforced_in_model(tmp_path: Path):
    """Per-entity bounds should be reflected in built model constraints."""
    s = _build_scheduler(tmp_path)
    s.set_visitor_meeting_bounds("Visitor 1", min_meetings=1, max_meetings=1)
    s.set_faculty_meeting_bounds("Faculty A", min_meetings=1, max_meetings=1)

    s._build_model(
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=4,
        min_faculty=0,
        max_group=1,
        enforce_breaks=False,
    )
    m = s.model
    assert m.min_faculty["Visitor 1"].lower == 1
    assert m.max_faculty["Visitor 1"].upper == 1
    assert m.min_visitors_constraint["Faculty A"].lower == 1
    assert m.max_visitors_constraint["Faculty A"].upper == 1


def test_require_break_slots_none_uses_all_slots(tmp_path: Path):
    """slots=None should normalize to all configured scheduler slots."""
    s = _build_scheduler(tmp_path)
    s.require_break("Visitor 1", slots=None, min_breaks=1)
    assert ("Visitor 1", tuple(s.time_slots), 1) in s._required_breaks


def test_forbid_and_require_slot_contradiction_branches(tmp_path: Path):
    """Exercise additional contradiction branches for forbid/require APIs."""
    s = _build_scheduler(tmp_path)
    s.require_meeting("Visitor 1", "Faculty A")
    with pytest.raises(ValueError, match="required across all slots"):
        s.forbid_meeting("Visitor 1", "Faculty A")
    with pytest.raises(ValueError, match="required across all slots"):
        s.forbid_meeting("Visitor 1", "Faculty A", time_slot=1)

    s2 = _build_scheduler(tmp_path)
    s2.require_meeting("Visitor 1", "Faculty A", time_slot=1)
    with pytest.raises(ValueError, match="required at slot"):
        s2.forbid_meeting("Visitor 1", "Faculty A")

    s3 = _build_scheduler(tmp_path)
    s3.forbid_meeting("Visitor 1", "Faculty A")
    with pytest.raises(ValueError, match="forbidden across all slots"):
        s3.require_meeting("Visitor 1", "Faculty A", time_slot=1)

    s4 = _build_scheduler(tmp_path)
    s4.forbid_meeting("Visitor 1", "Faculty A", time_slot=1)
    with pytest.raises(ValueError, match="forbidden in that slot"):
        s4.require_meeting("Visitor 1", "Faculty A", time_slot=1)


def test_build_model_defensive_skips_for_non_model_entities(tmp_path: Path):
    """Defensive model-injection branches should skip missing visitor/faculty keys."""
    s = _build_scheduler(tmp_path)
    s.add_external_faculty("Faculty C", available=[])  # in faculty dict, not in model faculty set
    s.forbid_meeting("Visitor 1", "Faculty C")
    s.forbid_meeting("Visitor 1", "Faculty C", time_slot=1)
    s._required_meetings_all_slots.add(("Ghost Visitor", "Faculty C"))
    s._required_meetings_by_slot.add(("Visitor 1", "Faculty C", 1))
    s._required_breaks.add(("Ghost Visitor", (1, 2), 1))

    s._build_model(
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=4,
        min_faculty=0,
        max_group=1,
        enforce_breaks=False,
    )
    assert hasattr(s.model, "user_hard_constraints")


def test_collect_presolve_issues_additional_edge_paths(tmp_path: Path):
    """Cover remaining pre-solve issue-collector branches with explicit states."""
    # unavailable faculty with required-any and required-specific (including duplicate slots)
    s = _build_scheduler(tmp_path)
    s.add_external_faculty("Faculty C", available=[])
    s._required_meetings_all_slots.add(("Visitor 1", "Faculty C"))
    s._required_meetings_by_slot.add(("Visitor 1", "Faculty C", 1))
    s._required_meetings_by_slot.add(("Visitor 1", "Faculty C", 2))
    s.set_faculty_meeting_bounds("Faculty C", min_meetings=1, max_meetings=2)
    issues = s._collect_presolve_hard_constraint_issues(
        min_visitors=0, max_visitors=4, min_faculty=0, max_group=1
    )
    text = "\n".join(issues)
    assert "has no available slots" in text
    assert "required in multiple slots" in text
    assert "set_faculty_meeting_bounds" in text

    # required-any candidate filtering branches: skip due specific pair, visitor slot forced, faculty slot forced
    s2 = _build_scheduler(tmp_path)
    s2._required_meetings_by_slot.add(("Visitor 1", "Faculty B", 1))  # visitor slot forced
    s2._required_meetings_by_slot.add(("Visitor 2", "Faculty A", 2))  # faculty slot forced
    s2._required_meetings_all_slots.add(("Visitor 1", "Faculty A"))
    s2._required_meetings_all_slots.add(("Visitor 1", "Faculty B"))
    s2._required_meetings_by_slot.add(("Visitor 1", "Faculty B", 2))  # same pair in specific => continue branch
    issues2 = s2._collect_presolve_hard_constraint_issues(
        min_visitors=0, max_visitors=4, min_faculty=0, max_group=1
    )
    assert any("no feasible slot remains" in msg for msg in issues2)

    # impossible visitor min due breaks (min > computed upper)
    s3 = _build_scheduler(tmp_path)
    s3.set_visitor_meeting_bounds("Visitor 1", min_meetings=1, max_meetings=None)
    s3.require_break("Visitor 1", slots=[1, 2], min_breaks=2)
    issues3 = s3._collect_presolve_hard_constraint_issues(
        min_visitors=0, max_visitors=4, min_faculty=0, max_group=1
    )
    assert any("Visitor 'Visitor 1' has min required meetings" in msg for msg in issues3)

    # invalid effective bounds via direct internal mutation (API intentionally blocks this)
    s4 = _build_scheduler(tmp_path)
    s4._visitor_meeting_bounds["Visitor 1"] = {"min_meetings": 2, "max_meetings": 1}
    s4._faculty_meeting_bounds["Faculty A"] = {"min_meetings": 2, "max_meetings": 1}
    issues4 = s4._collect_presolve_hard_constraint_issues(
        min_visitors=0, max_visitors=4, min_faculty=0, max_group=1
    )
    assert any("Invalid effective visitor bounds" in msg for msg in issues4)
    assert any("Invalid effective faculty bounds" in msg for msg in issues4)

    # faculty min above feasible upper bound
    s5 = _build_scheduler(tmp_path)
    s5.set_faculty_meeting_bounds("Faculty A", min_meetings=3, max_meetings=4)
    issues5 = s5._collect_presolve_hard_constraint_issues(
        min_visitors=0, max_visitors=4, min_faculty=0, max_group=1
    )
    assert any("Faculty 'Faculty A' has min required meetings" in msg for msg in issues5)

    # unavailable faculty required-any without specific requirement should flow through _allowed_slots early return
    s6 = _build_scheduler(tmp_path)
    s6.add_external_faculty("Faculty C", available=[])
    s6._required_meetings_all_slots.add(("Visitor 1", "Faculty C"))
    issues6 = s6._collect_presolve_hard_constraint_issues(
        min_visitors=0, max_visitors=4, min_faculty=0, max_group=1
    )
    assert any("Cannot satisfy require_meeting('Visitor 1', 'Faculty C')" in msg for msg in issues6)


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
