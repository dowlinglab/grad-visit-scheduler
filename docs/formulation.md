# Mathematical Formulation

This page documents the mixed-integer linear programming (MILP) model implemented in `Scheduler._build_model`.
For usage-oriented movement configuration examples, see [Building Movement and Staggered Starts](movement.md).

## Code-Aligned Notation

This table maps the mathematical symbols to the exact Pyomo components in the code.

| Math symbol | Code component | Meaning |
| --- | --- | --- |
| $\mathcal{S}$ | `m.visitors` | Visitor set |
| $\mathcal{F}$ | `m.faculty` | Faculty set with non-empty availability |
| $\mathcal{T}$ | `m.time` | Time-slot index set |
| $\mathcal{K}$ | `m.buildings` | Building set |
| $\mathcal{F}_k$ | `m.faculty_by_building[k]` | Faculty assigned to building $k$ |
| $\mathcal{B}$ | `m.break_options` | Candidate break slots |
| $w_{sf}$ | `m.weights[s, f]` | Utility weight for visitor-faculty match |
| $p$ | `m.penalty` | Group penalty coefficient |
| $y_{sft}$ | `m.y[s, f, t]` | Meeting assignment decision variable |
| $z_{ft}$ | `m.beyond_one_visitor[f, t]` | Visitors beyond one in a meeting |
| $q_f$ | `m.faculty_too_many_meetings[f]` | Overload indicator |
| $\beta_{skt}$ | `m.in_building[s, k, t]` | Visitor in building $k$ at slot $t$ (travel policies) |
| $r_{ft}$ | `m.faculty_breaks[f, t]` | Faculty break indicator |
| $\underline{L}_s,\overline{U}_s$ | `set_visitor_meeting_bounds(...)` + `min_faculty` | Effective visitor min/max meetings |
| $\underline{L}_f,\overline{U}_f$ | `set_faculty_meeting_bounds(...)` + `min_visitors/max_visitors` | Effective faculty min/max meetings |

## Worked Example Dataset

The repository includes a formulation-focused dataset:

- `examples/faculty_formulation.yaml`
- `examples/config_formulation.yaml`
- `examples/data_formulation_visitors.csv`

Dataset size:
- 6 faculty (`Prof. A` through `Prof. F`)
- 4 time slots
- 10 visitors
- buildings: `ABC` and `XYZ`
- topic areas: `Energy`, `Bio`, `Theory`
- break window: slots 2 and 3

Runner script:
- `scripts/run_formulation_example.py`

Faculty availability conflicts in this example:

| Faculty | Available slots | Unavailable slots |
| --- | --- | --- |
| Prof. A | 1, 2, 3, 4 | None |
| Prof. B | 1, 2, 4 | 3 |
| Prof. C | 1, 3, 4 | 2 |
| Prof. D | 2, 3, 4 | 1 |
| Prof. E | 1, 2, 3 | 4 |
| Prof. F | 1, 3, 4 | 2 |

## Student Preference Summary

| Visitor | Prof1 | Prof2 | Prof3 | Prof4 | Area1 | Area2 |
| --- | --- | --- | --- | --- | --- | --- |
| Visitor 01 | Prof. A | Prof. C | Prof. E | Prof. F | Energy | Theory |
| Visitor 02 | Prof. B | Prof. D | Prof. F | Prof. C | Bio | Energy |
| Visitor 03 | Prof. C | Prof. A | Prof. E | Prof. B | Theory | Energy |
| Visitor 04 | Prof. D | Prof. F | Prof. B | Prof. A | Energy | Bio |
| Visitor 05 | Prof. E | Prof. C | Prof. A | Prof. D | Bio | Theory |
| Visitor 06 | Prof. F | Prof. B | Prof. D | Prof. E | Theory | Bio |
| Visitor 07 | Prof. A | Prof. E | Prof. C | Prof. D | Energy | Bio |
| Visitor 08 | Prof. B | Prof. F | Prof. D | Prof. A | Bio | Theory |
| Visitor 09 | Prof. C | Prof. E | Prof. A | Prof. B | Theory | Energy |
| Visitor 10 | Prof. D | Prof. B | Prof. F | Prof. C | Energy | Theory |

## Sets and Indices

- $s \in \mathcal{S}$: visitors
- $f \in \mathcal{F}$: faculty with at least one available time slot
- $t \in \mathcal{T} = \{1, \dots, T\}$: time slots
- $k \in \mathcal{K}$: buildings
- $\mathcal{F}_k \subseteq \mathcal{F}$: faculty located in building $k$
- $\mathcal{B} \subseteq \mathcal{T}$: configured break slot options

## Parameters

- $w_{sf}$: utility weight for assigning visitor $s$ to faculty $f$
- $p \ge 0$: group meeting penalty (`group_penalty`)
- $L_f$: minimum visitors per faculty (`min_visitors`)
- $U_f$: maximum visitors per faculty (`max_visitors`)
- $L_s$: minimum faculty meetings per visitor (`min_faculty`)
- $\underline{L}_s,\overline{U}_s$: effective visitor bounds after optional per-visitor overrides
- $\underline{L}_f,\overline{U}_f$: effective faculty bounds after optional per-faculty overrides
- $G$: maximum group size in a faculty-time meeting (`max_group`)
- $a_{ft} \in \{0,1\}$: 1 if faculty $f$ is available at slot $t$

## Decision Variables

- $y_{sft} \in \{0,1\}$: 1 if visitor $s$ meets faculty $f$ at time $t$
- $z_{ft} \ge 0$: number of visitors beyond one in faculty-time meeting $(f,t)$
- $q_f \in \{0,1\}$: overload indicator for faculty $f$
- $\beta_{skt} \in \{0,1\}$: visitor $s$ is in building $k$ at slot $t$ (when `movement.policy` is `travel_time` or `nonoverlap_time`)
- $r_{ft} \in \{0,1\}$: faculty $f$ is on break at candidate break slot $t \in \mathcal{B}$

## Objective

Maximize preference satisfaction minus group/overload penalties:

$$
\max \sum_{s \in \mathcal{S}} \sum_{f \in \mathcal{F}} \sum_{t \in \mathcal{T}} w_{sf} y_{sft}
- p \sum_{f \in \mathcal{F}} \sum_{t \in \mathcal{T}} z_{ft}
- 3p \sum_{f \in \mathcal{F}} q_f
$$

Interpretation:
- First term rewards satisfying visitor preferences.
- Second term discourages group meetings larger than one visitor.
- Third term discourages faculty loads beyond the soft threshold used in the implementation.

## Constraints

### 1. Faculty availability

$$
y_{sft} \le a_{ft}
\quad \forall s,f,t
$$

Meetings can only occur when faculty are available.

### 2. Faculty minimum and maximum total meetings (with optional overrides)

$$
\sum_{s \in \mathcal{S}} \sum_{t \in \mathcal{T}} y_{sft} \ge \underline{L}_f
\quad \forall f
$$

$$
\sum_{s \in \mathcal{S}} \sum_{t \in \mathcal{T}} y_{sft} \le \overline{U}_f
\quad \forall f
$$

### 3. Visitor cannot attend simultaneous meetings

$$
\sum_{f \in \mathcal{F}} y_{sft} \le 1
\quad \forall s,t
$$

### 4. Visitor minimum and optional maximum total meetings

$$
\sum_{f \in \mathcal{F}} \sum_{t \in \mathcal{T}} y_{sft}
\ge \underline{L}_s
\quad \forall s
$$

The default lower bound is $\underline{L}_s=\min\left(L_s,\left|\mathcal{T}_s^{\text{avail}}\right|\right)$, then overridden by `set_visitor_meeting_bounds` when provided.

When a visitor-specific maximum is configured:

$$
\sum_{f \in \mathcal{F}} \sum_{t \in \mathcal{T}} y_{sft}
\le \overline{U}_s
\quad \forall s \text{ with override}
$$

### 5. Visitor meets same faculty at most once

$$
\sum_{t \in \mathcal{T}} y_{sft} \le 1
\quad \forall s,f
$$

### 6. Excess visitors per faculty-time slot

$$
z_{ft} \ge \sum_{s \in \mathcal{S}} y_{sft} - 1
\quad \forall f,t
$$

This linearizes the "beyond one visitor" quantity used in the objective penalty.

### 7. Faculty overload indicator

$$
2q_f \ge
\sum_{s \in \mathcal{S}} \sum_{t \in \mathcal{T}} y_{sft}
- U_f + 2
\quad \forall f
$$

This activates $q_f$ when total meetings exceed the soft threshold $U_f - 2$.

### 8. Maximum group size per meeting

$$
\sum_{s \in \mathcal{S}} y_{sft} \le G
\quad \forall f,t
$$

### 9. Building phase constraints (`movement.phase_slot`)

Each building $k$ has an earliest allowed meeting slot $\phi_k$:

$$
y_{sft} \le \mathbf{1}\!\left[t \ge \phi_{\text{building}(f)}\right]
\quad \forall s,f,t
$$

This supports staggered schedules such as "Building A first" or "Building B first"
without requiring a dedicated mode.

### 10. Travel-time occupancy and lag constraints (`movement.policy = travel_time` or `nonoverlap_time`)

When travel-time constraints are enabled, occupancy indicators are linked by:

$$
\sum_{f \in \mathcal{F}_k} y_{sft} \le \beta_{skt}
\quad \forall s,k,t
$$

For each building pair $(k,\ell)$ with lag $\tau_{k\ell} > 0$, transitions within
the lag window are forbidden:

$$
\beta_{sk t_1} + \beta_{s\ell t_2} \le 1,
\quad \forall s,\; k \ne \ell,\; 0 < t_2-t_1 \le \tau_{k\ell}
$$

When `travel_slots: auto` or `policy: nonoverlap_time` is used, $\tau_{k\ell}$
is derived from absolute slot timestamps so overlapping real-time transitions
are disallowed (optionally with additional `min_buffer_minutes`).

### 11. Visitor break requirement

Applied when automatic student break constraints are enabled (`movement` legacy
`NO_OFFSET` compatibility, `student_breaks > 0`, or legacy
`enforce_breaks=True`):

$$
\sum_{f \in \mathcal{F}} \sum_{t \in \mathcal{B}} y_{sft}
\le |\mathcal{B}| - 1
\quad \forall s
$$

More generally, each visitor must have at least `student_breaks` breaks during
the configured break window.

### 12. Faculty break variables and requirement

Applied when break constraints are enabled:

$$
\sum_{s \in \mathcal{S}} y_{sft} \le G(1-r_{ft})
\quad \forall f,\; t \in \mathcal{B}
$$

If $r_{ft}=1$, faculty $f$ has no meeting at break slot $t$.

$$
u_f + \sum_{t \in \mathcal{B}} r_{ft} \ge b
\quad \forall f
$$

Here $b$ is the normalized faculty break requirement derived from
`faculty_breaks`, and $u_f$ counts faculty-unavailable slots outside the
configured break window that already count as breaks. Unavailable slots inside
the break window are fixed to $r_{ft}=1$ in the implementation. Legacy
`enforce_breaks=True` maps to `faculty_breaks=1` and `student_breaks=1`.

### 13. Fixed unavailability for visitors

For visitor-specific availability restrictions, decision variables are fixed to zero:

$$
y_{sft} = 0
\quad \forall (s,t) \text{ not available to visitor } s,\; \forall f
$$

### 14. User-specified visitor/faculty hard constraints (optional)

The APIs `forbid_meeting`, `require_meeting`, and `require_break` add explicit hard constraints:

All-slot forbid (`forbid_meeting(s,f)`):

$$
y_{sft}=0 \quad \forall t \in \mathcal{T}
$$

Slot-specific forbid (`forbid_meeting(s,f,t^\*)`):

$$
y_{sf t^\*}=0
$$

All-slot require (`require_meeting(s,f)`):

$$
\sum_{t \in \mathcal{T}} y_{sft}=1
$$

Slot-specific require (`require_meeting(s,f,t^\*)`):

$$
y_{sf t^\*}=1
$$

Required breaks (`require_break(s,\mathcal{T}',b)`):

$$
\sum_{f \in \mathcal{F}}\sum_{t\in\mathcal{T}'} y_{sft}\le |\mathcal{T}'|-b
$$

where $b$ is `min_breaks`.

## Top-N No-Good Cuts (Optional Multi-Solution Extension)

When generating ranked alternatives, the model adds one no-good cut after each
feasible solution to exclude the exact same binary assignment vector in later
iterations.

Let $\mathcal{I}$ be all assignment indices $(s,f,t)$ and let
$\mathcal{A}^{(k)} \subseteq \mathcal{I}$ be the active assignment set in
rank-$k$ solution. The no-good cut for solution $k$ is:

$$
\sum_{i \in \mathcal{A}^{(k)}} \left(1 - y_i\right)
+ \sum_{i \in \mathcal{I}\setminus \mathcal{A}^{(k)}} y_i
\ge 1
$$

This enforces that at least one binary variable differs from solution $k$.

## Notes on Implementation

- The model is assembled in `Scheduler._build_model` and solved in `Scheduler._solve_model`.
- Feasibility checks and diagnostics are available through `has_feasible_solution` and `infeasibility_report`.
- Constraint activation depends on movement policy plus the resolved
  `faculty_breaks` / `student_breaks` values exactly as documented above.
- Legacy mode-specific movement constraints are superseded by the
  `movement.phase_slot` and `movement.travel_slots` formulation above.
- When advanced user hard constraints or per-entity bounds are configured,
  pre-solve consistency checks run via `_run_presolve_hard_constraint_checks`.
  These checks catch obvious contradictions before solver execution and raise
  clear `ValueError` messages.
- `debug_infeasible=False` (default): fail fast before model build.
- `debug_infeasible=True`: build model first, then raise pre-solve errors so
  advanced users can inspect `s.model` (for example before IIS workflows).

## Example Solutions

The table below was generated by solving the worked dataset with:

- `solver=Solver.HIGHS`
- `group_penalty=0.2`
- `min_visitors=2`
- `max_visitors=8`
- `min_faculty=1`
- `max_group=2`
- `faculty_breaks=1`
- `student_breaks=1`

Solver metrics:
- total utility: `113.5`
- total excess-visitors penalty term: `0.2 * 13 = 2.6`
- faculty overload indicators: `0`
- objective value: `110.9`

### Solver-Generated Visitor Schedule

| Visitor | Slot 1 | Slot 2 | Slot 3 | Slot 4 |
| --- | --- | --- | --- | --- |
| Visitor 01 | Prof. E | Prof. A | Break | Prof. C |
| Visitor 02 | Prof. B | Break | Prof. D | Prof. F |
| Visitor 03 | Prof. E | Prof. A | Break | Prof. C |
| Visitor 04 | Prof. F | Prof. B | Break | Prof. D |
| Visitor 05 | Prof. C | Prof. E | Break | Prof. A |
| Visitor 06 | Prof. F | Prof. D | Break | Prof. B |
| Visitor 07 | Prof. A | Prof. E | Break | Prof. D |
| Visitor 08 | Prof. A | Break | Prof. F | Prof. B |
| Visitor 09 | Prof. C | Break | Prof. E | Prof. A |
| Visitor 10 | Prof. B | Prof. D | Break | Prof. F |

### Solver-Generated Faculty Load Summary

| Faculty | Total meetings | Slot 1 | Slot 2 | Slot 3 | Slot 4 |
| --- | ---: | --- | --- | --- | --- |
| Prof. A | 6 | 2 | 2 | 0 | 2 |
| Prof. B | 5 | 2 | 1 | 0 | 2 |
| Prof. C | 4 | 2 | 0 | 0 | 2 |
| Prof. D | 5 | 0 | 2 | 1 | 2 |
| Prof. E | 5 | 2 | 2 | 1 | 0 |
| Prof. F | 5 | 2 | 0 | 1 | 2 |
