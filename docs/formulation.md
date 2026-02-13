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
| $\beta_{skt}$ | `m.in_building[s, k, t]` | Visitor in building $k$ at slot $t$ (travel policy only) |
| $r_{ft}$ | `m.faculty_breaks[f, t]` | Faculty break indicator |

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
- $G$: maximum group size in a faculty-time meeting (`max_group`)
- $a_{ft} \in \{0,1\}$: 1 if faculty $f$ is available at slot $t$

## Decision Variables

- $y_{sft} \in \{0,1\}$: 1 if visitor $s$ meets faculty $f$ at time $t$
- $z_{ft} \ge 0$: number of visitors beyond one in faculty-time meeting $(f,t)$
- $q_f \in \{0,1\}$: overload indicator for faculty $f$
- $\beta_{skt} \in \{0,1\}$: visitor $s$ is in building $k$ at slot $t$ (only when `movement.policy = travel_time`)
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

### 2. Faculty minimum and maximum total meetings

$$
\sum_{s \in \mathcal{S}} \sum_{t \in \mathcal{T}} y_{sft} \ge L_f
\quad \forall f
$$

$$
\sum_{s \in \mathcal{S}} \sum_{t \in \mathcal{T}} y_{sft} \le U_f
\quad \forall f
$$

### 3. Visitor cannot attend simultaneous meetings

$$
\sum_{f \in \mathcal{F}} y_{sft} \le 1
\quad \forall s,t
$$

### 4. Visitor minimum total meetings

$$
\sum_{f \in \mathcal{F}} \sum_{t \in \mathcal{T}} y_{sft}
\ge \min\left(L_s, \left|\mathcal{T}_s^{\text{avail}}\right|\right)
\quad \forall s
$$

The implemented lower bound is clipped by each visitor's own availability window.

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

### 10. Travel-time occupancy and lag constraints (`movement.policy = travel_time`)

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

### 11. Visitor break requirement

Applied when break constraints are enabled (`movement` legacy `NO_OFFSET` compatibility or `enforce_breaks=True`):

$$
\sum_{f \in \mathcal{F}} \sum_{t \in \mathcal{B}} y_{sft}
\le |\mathcal{B}| - 1
\quad \forall s
$$

Each visitor must have at least one break during the configured break window.

### 12. Faculty break variables and requirement

Applied when break constraints are enabled:

$$
\sum_{s \in \mathcal{S}} y_{sft} \le G(1-r_{ft})
\quad \forall f,\; t \in \mathcal{B}
$$

If $r_{ft}=1$, faculty $f$ has no meeting at break slot $t$.

$$
\sum_{t \in \mathcal{B}} r_{ft} \ge 1
\quad \forall f \text{ with full-slot availability}
$$

Faculty with limited availability are exempt in the implementation.

### 13. Fixed unavailability for visitors

For visitor-specific availability restrictions, decision variables are fixed to zero:

$$
y_{sft} = 0
\quad \forall (s,t) \text{ not available to visitor } s,\; \forall f
$$

## Notes on Implementation

- The model is assembled in `Scheduler._build_model` and solved in `Scheduler._solve_model`.
- Feasibility checks and diagnostics are available through `has_feasible_solution` and `infeasibility_report`.
- Constraint activation depends on movement policy and `enforce_breaks` exactly as documented above.
- Legacy mode-specific movement constraints are superseded by the
  `movement.phase_slot` and `movement.travel_slots` formulation above.

## Example Solutions

The table below was generated by solving the worked dataset with:

- `solver=Solver.HIGHS`
- `group_penalty=0.2`
- `min_visitors=2`
- `max_visitors=8`
- `min_faculty=1`
- `max_group=2`
- `enforce_breaks=True`

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
