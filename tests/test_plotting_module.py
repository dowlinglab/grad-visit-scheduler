"""Tests for plotting module re-exports."""

import warnings

import pytest

from grad_visit_scheduler import plotting


def test_plotting_module_exports_core_helpers():
    """plotting module should re-export helper functions from core."""
    assert plotting.schedule_axes is not None
    with pytest.warns(UserWarning, match="Ambiguous bare slot label"):
        assert plotting.slot2min("1:00-1:25") == (780, 805)
    assert plotting.slot2min("13:00-13:25") == (780, 805)
    assert plotting.slot2min("8:30 AM-8:55 AM") == (510, 535)
    assert plotting.abbreviate_name("Jane Doe") == "Jane D."
    assert set(plotting.__all__) == {"schedule_axes", "slot2min", "abbreviate_name"}

    ax = plotting.schedule_axes(figsize=(4, 3), nslots=2)
    assert ax.get_xlabel() == "Time"
    assert len(ax.get_xticks()) >= 2


def test_schedule_axes_uses_concrete_time_labels_for_ticks_and_limits():
    """schedule_axes should derive bounds from real slot labels when provided."""
    ax = plotting.schedule_axes(
        figsize=(4, 3),
        time_labels={
            "Virtual": [
                "8:30-8:55",
                "9:00-9:25",
                "9:30-9:55",
                "10:00-10:25",
                "10:30-10:55",
            ]
        },
    )

    assert ax.get_xlim() == pytest.approx((510, 660))
    assert list(ax.get_xticks()) == [510, 525, 540, 555, 570, 585, 600, 615, 630, 645, 660]
    assert [tick.get_text() for tick in ax.get_xticklabels()][:3] == ["8:30", "8:45", "9:00"]


@pytest.mark.parametrize(
    ("slot_label", "expected"),
    [
        ("8:30 AM-8:55 AM", (510, 535)),
        ("8:30am-8:55am", (510, 535)),
        ("12:00 PM-12:25 PM", (720, 745)),
        ("12:00 AM-12:25 AM", (0, 25)),
        ("1:00 PM-1:25 PM", (780, 805)),
        ("13:00-13:25", (780, 805)),
    ],
)
def test_slot2min_accepts_meridiem_and_24_hour_labels(slot_label, expected):
    """slot2min should support meridiem-qualified and 24-hour labels."""
    assert plotting.slot2min(slot_label) == expected


@pytest.mark.parametrize(
    "slot_label",
    [
        "bad",
        "1:0-1:25",
        "1:00/1:25",
        "1:60-2:00",
        "2:10-2:10",
        "2:30-2:25",
        "8:30 AM-8:55",
        "13:00 PM-13:25 PM",
        "0:30 AM-0:55 AM",
    ],
)
def test_slot2min_rejects_invalid_slot_labels(slot_label):
    """slot2min should fail with clear errors on malformed/non-increasing labels."""
    with pytest.raises(ValueError):
        plotting.slot2min(slot_label)


def test_slot2min_rejects_non_string_input():
    """slot2min should fail fast for non-string labels."""
    with pytest.raises(ValueError, match="string"):
        plotting.slot2min(125)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("slot_label", "expected"),
    [
        ("1:30-1:55", (810, 835)),
        ("6:00-6:25", (1080, 1105)),
        ("7:00-7:25", (420, 445)),
        ("11:00-11:25", (660, 685)),
        ("12:00-12:25", (720, 745)),
    ],
)
def test_slot2min_infers_bare_12_hour_labels_with_warning(slot_label, expected):
    """Bare 12-hour slot labels should follow the visit-day AM/PM heuristic."""
    with pytest.warns(UserWarning, match="interpreted using visit-day heuristics"):
        assert plotting.slot2min(slot_label) == expected


def test_slot2min_only_warns_once_per_ambiguous_label():
    """Repeated parsing of the same ambiguous label should not warn repeatedly."""
    with pytest.warns(UserWarning, match="Ambiguous bare slot label"):
        assert plotting.slot2min("2:00-2:25") == (840, 865)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert plotting.slot2min("2:00-2:25") == (840, 865)
    assert not caught
