"""Tests for plotting module re-exports."""

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
