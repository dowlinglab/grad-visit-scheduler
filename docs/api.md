# API Reference

The API pages below are generated from code docstrings.

```{eval-rst}
.. automodule:: grad_visit_scheduler
```

Top-level imports provided by `grad_visit_scheduler`:

- `Scheduler`
- `Mode`
- `MovementPolicy`
- `Solver`
- `FacultyStatus`
- `SolutionResult`
- `SolutionSet`
- `scheduler_from_configs`
- `load_faculty_catalog`
- `load_run_config`
- `build_times_by_building`
- `export_visitor_docx`

Preferred interface note: use run-config `movement:` settings and
`MovementPolicy`; `Mode` remains as a legacy compatibility enum.

## Top-N Review Helper

`SolutionSet.summarize(...)` packages the common "review top-N solutions" workflow:

- Full summary dataframe (`report["summary"]`)
- Compact comparison dataframe (`report["compact"]`)
- Optional ranked plot generation
- Optional ranked DOCX export

Internal review pattern (keep rank labels visible in plot titles):

```python
top = s.schedule_visitors_top_n(n_solutions=3, enforce_breaks=True)
report = top.summarize(
    ranks_to_plot=(1, 2),
    save_files=True,
    show_solution_rank=True,
    plot_prefix="internal_review",
)
print(report["summary"])
print(report["compact"])
```

External-facing pattern (hide rank labels for faculty/visitor handouts):

```python
top = s.schedule_visitors_top_n(n_solutions=3, enforce_breaks=True)
report = top.summarize(
    ranks_to_plot=(1,),
    save_files=True,
    show_solution_rank=False,
    plot_prefix="final_schedule",
    export_docx=True,
    docx_prefix="visitor_schedule_final",
)
```

### Top-N Exhaustion Semantics (Developer Note)

When `schedule_visitors_top_n(n_solutions=...)` requests more schedules than are
uniquely feasible, the solve loop stops after the first infeasible no-good-cut
iteration. In this case:

- `SolutionSet` contains all feasible unique solutions found so far.
- `Scheduler.last_solution_set` points to that `SolutionSet`.
- `Scheduler.results` / `has_feasible_solution()` remain aligned with the last
  feasible loaded model state.
- `Scheduler._current_solution_result()` therefore returns the last feasible
  schedule (with rank `1` as a current-state snapshot rank).

This behavior is intentional so legacy scheduler-level plotting/export methods
continue to operate after top-N exhaustion.

## Core Model API

```{eval-rst}
.. automodule:: grad_visit_scheduler.core
   :members:
   :private-members:
   :special-members: __init__
```

## Config API

```{eval-rst}
.. automodule:: grad_visit_scheduler.config
   :members:
```

## Export API

```{eval-rst}
.. automodule:: grad_visit_scheduler.export
   :members:
```

## Data API

```{eval-rst}
.. automodule:: grad_visit_scheduler.data
   :members:
```
