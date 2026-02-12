# API Reference

The API pages below are generated from code docstrings.

```{eval-rst}
.. automodule:: grad_visit_scheduler
```

Top-level imports provided by `grad_visit_scheduler`:

- `Scheduler`
- `Mode`
- `Solver`
- `FacultyStatus`
- `SolutionResult`
- `SolutionSet`
- `scheduler_from_configs`
- `load_faculty_catalog`
- `load_run_config`
- `build_times_by_building`
- `export_visitor_docx`

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
