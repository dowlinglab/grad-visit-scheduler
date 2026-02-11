Examples live here. Suggested workflow:

- Copy and adjust a run config from this folder.
- Point to a visitor CSV (e.g., `examples/data_fake_visitors.csv`).
- Build a `Scheduler` with `scheduler_from_configs` and run.

Minimal example:

```python
from grad_visit_scheduler import scheduler_from_configs, Mode, Solver

s = scheduler_from_configs(
    "examples/faculty_example.yaml",
    "examples/config_basic.yaml",
    "examples/data_fake_visitors.csv",
    mode=Mode.NO_OFFSET,
    solver=Solver.HIGHS,
)

s.schedule_visitors(
    group_penalty=0.1,
    min_visitors=0,
    max_visitors=4,
    min_faculty=1,
    max_group=2,
    enforce_breaks=True,
    tee=False,
    run_name="demo",
)

if s.has_feasible_solution():
    s.show_visitor_schedule(save_files=True)
```

Notes:
- `building_order` declares which building is Building A vs Building B.
- Use `Mode.BUILDING_A_FIRST`, `Mode.BUILDING_B_FIRST`, or `Mode.NO_OFFSET` to control movement.

Formulation-focused example:
- `faculty_formulation.yaml`: three-faculty catalog used in docs.
- `config_formulation.yaml`: four slots with two break options (`[2, 3]`).
- `data_formulation_visitors.csv`: ten visitors for worked-formulation examples.
