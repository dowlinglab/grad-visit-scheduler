"""Tests for plotting module re-exports."""

import pytest

from grad_visit_scheduler import plotting


def test_plotting_module_exports_core_helpers():
    """plotting module should re-export helper functions from core."""
    assert plotting.schedule_axes is not None
    assert plotting.slot2min("1:00-1:25") == (60, 85)
    assert plotting.abbreviate_name("Jane Doe") == "Jane D."
    assert set(plotting.__all__) == {"schedule_axes", "slot2min", "abbreviate_name"}

    ax = plotting.schedule_axes(figsize=(4, 3), nslots=2)
    assert ax.get_xlabel() == "Time (PM)"
    assert len(ax.get_xticks()) >= 2


@pytest.mark.parametrize(
    "slot_label",
    [
        "bad",
        "1:0-1:25",
        "1:00/1:25",
        "1:60-2:00",
        "2:10-2:10",
        "2:30-2:25",
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
