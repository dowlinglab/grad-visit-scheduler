# Advanced Customization

This page collects advanced scheduling controls that most users do not need for
basic runs.

## Hard Constraints

Use these APIs before solving to force or forbid specific outcomes:

```python
# 1) forbid_meeting(visitor, faculty, time_slot=None)
s.forbid_meeting("Visitor 1", "Prof. C")         # forbid all slots
s.forbid_meeting("Visitor 2", "Prof. A", 3)      # forbid only slot 3

# 2) require_meeting(visitor, faculty, time_slot=None)
s.require_meeting("Visitor 3", "Prof. B")        # require exactly once across all slots
s.require_meeting("Visitor 4", "Prof. D", 2)     # require slot 2 specifically

# 3) require_break(visitor, slots=None, min_breaks=1)
s.require_break("Visitor 5")                     # at least one break in all slots
s.require_break("Visitor 6", slots=[2, 3], min_breaks=1)
```

These are hard MILP constraints (not preference weights). Duplicate calls are
idempotent.

## Optional Per-Entity Meeting Bounds

When global meeting bounds are too strict for a specific person, use targeted
overrides:

```python
# Visitor-specific override (None => use global defaults)
s.set_visitor_meeting_bounds("Visitor 1", min_meetings=1, max_meetings=2)
s.set_visitor_meeting_bounds("Visitor 2", min_meetings=None, max_meetings=None)  # clear override

# Faculty-specific override (None => use global defaults)
s.set_faculty_meeting_bounds("Prof. A", min_meetings=1, max_meetings=4)
s.set_faculty_meeting_bounds("Prof. B", min_meetings=None, max_meetings=None)  # clear override
```

Override precedence:

- Visitor bounds override global `min_faculty` for that visitor.
- Faculty bounds override global `min_visitors` / `max_visitors` for that faculty.
- Hard constraints (`require_*`, `forbid_*`) remain hard.

## Pre-Solve Checks

When advanced hard constraints or per-entity bounds are configured, the
scheduler runs pre-solve consistency checks and raises `ValueError` for obvious
contradictions (for example, required meetings that exceed max bounds, or
slot-specific conflicts).

Error messages include actionable suggestions such as:

- `set_visitor_meeting_bounds(...)`
- `set_faculty_meeting_bounds(...)`

This helps non-expert users avoid solver-level infeasibility diagnostics.

## Debugging Infeasibility

By default, pre-checks fail fast before model construction:

```python
s.schedule_visitors(
    min_faculty=2,
    debug_infeasible=False,  # default
)
```

For expert workflows, use:

```python
s.schedule_visitors(
    min_faculty=2,
    debug_infeasible=True,
)
```

With `debug_infeasible=True`, the model is built first, then pre-check errors
are raised. This leaves `s.model` available for IIS/manual inspection.

The same option is available on `schedule_visitors_top_n(...)`.
