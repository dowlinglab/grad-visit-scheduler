# Mathematical Formulation

This page documents the mixed-integer linear programming (MILP) model implemented in `Scheduler._build_model`.

## Code-Aligned Notation

This table maps the mathematical symbols to the exact Pyomo components in the code.

| Math symbol | Code component | Meaning |
| --- | --- | --- |
| \(\mathcal{S}\) | `m.visitors` | Visitor set |
| \(\mathcal{F}\) | `m.faculty` | Faculty set with non-empty availability |
| \(\mathcal{T}\) | `m.time` | Time-slot index set |
| \(\mathcal{F}_A\) | `m.building_a` | Faculty in building A |
| \(\mathcal{F}_B\) | `m.building_b` | Faculty in building B |
| \(\mathcal{B}\) | `m.break_options` | Candidate break slots |
| \(w_{sf}\) | `m.weights[s, f]` | Utility weight for visitor-faculty match |
| \(p\) | `m.penalty` | Group penalty coefficient |
| \(y_{sft}\) | `m.y[s, f, t]` | Meeting assignment decision variable |
| \(z_{ft}\) | `m.beyond_one_visitor[f, t]` | Visitors beyond one in a meeting |
| \(q_f\) | `m.faculty_too_many_meetings[f]` | Overload indicator |
| \(A_{st}\) | `m.bldg_a[s, t]` | Visitor in building A at slot \(t\) |
| \(B_{st}\) | `m.bldg_b[s, t]` | Visitor in building B at slot \(t\) |
| \(r_{ft}\) | `m.faculty_breaks[f, t]` | Faculty break indicator |

## Worked Example Dataset

The repository includes a formulation-focused dataset:

- `examples/faculty_formulation.yaml`
- `examples/config_formulation.yaml`
- `examples/data_formulation_visitors.csv`

Dataset size:
- 3 faculty
- 4 time slots
- 10 visitors
- break window: slots 2 and 3

Runner script:
- `scripts/run_formulation_example.py`

## Sets and Indices

- \(s \in \mathcal{S}\): visitors
- \(f \in \mathcal{F}\): faculty with at least one available time slot
- \(t \in \mathcal{T} = \{1, \dots, T\}\): time slots
- \(\mathcal{F}_A \subseteq \mathcal{F}\): faculty located in building A
- \(\mathcal{F}_B \subseteq \mathcal{F}\): faculty located in building B
- \(\mathcal{B} \subseteq \mathcal{T}\): configured break slot options

## Parameters

- \(w_{sf}\): utility weight for assigning visitor \(s\) to faculty \(f\)
- \(p \ge 0\): group meeting penalty (`group_penalty`)
- \(L_f\): minimum visitors per faculty (`min_visitors`)
- \(U_f\): maximum visitors per faculty (`max_visitors`)
- \(L_s\): minimum faculty meetings per visitor (`min_faculty`)
- \(G\): maximum group size in a faculty-time meeting (`max_group`)
- \(a_{ft} \in \{0,1\}\): 1 if faculty \(f\) is available at slot \(t\)

## Decision Variables

- \(y_{sft} \in \{0,1\}\): 1 if visitor \(s\) meets faculty \(f\) at time \(t\)
- \(z_{ft} \ge 0\): number of visitors beyond one in faculty-time meeting \((f,t)\)
- \(q_f \in \{0,1\}\): overload indicator for faculty \(f\)
- \(A_{st} \in \{0,1\}\): visitor \(s\) is in building A at time \(t\)
- \(B_{st} \in \{0,1\}\): visitor \(s\) is in building B at time \(t\)
- \(r_{ft} \in \{0,1\}\): faculty \(f\) is on break at candidate break slot \(t \in \mathcal{B}\)

## Objective

Maximize preference satisfaction minus group/overload penalties:

\[
\max \sum_{s \in \mathcal{S}} \sum_{f \in \mathcal{F}} \sum_{t \in \mathcal{T}} w_{sf} y_{sft}
- p \sum_{f \in \mathcal{F}} \sum_{t \in \mathcal{T}} z_{ft}
- 3p \sum_{f \in \mathcal{F}} q_f
\]

Interpretation:
- First term rewards satisfying visitor preferences.
- Second term discourages group meetings larger than one visitor.
- Third term discourages faculty loads beyond the soft threshold used in the implementation.

## Constraints

### 1. Faculty availability

\[
y_{sft} \le a_{ft}
\quad \forall s,f,t
\]

Meetings can only occur when faculty are available.

### 2. Faculty minimum and maximum total meetings

\[
\sum_{s \in \mathcal{S}} \sum_{t \in \mathcal{T}} y_{sft} \ge L_f
\quad \forall f
\]

\[
\sum_{s \in \mathcal{S}} \sum_{t \in \mathcal{T}} y_{sft} \le U_f
\quad \forall f
\]

### 3. Visitor cannot attend simultaneous meetings

\[
\sum_{f \in \mathcal{F}} y_{sft} \le 1
\quad \forall s,t
\]

### 4. Visitor minimum total meetings

\[
\sum_{f \in \mathcal{F}} \sum_{t \in \mathcal{T}} y_{sft}
\ge \min\left(L_s, \left|\mathcal{T}_s^{\text{avail}}\right|\right)
\quad \forall s
\]

The implemented lower bound is clipped by each visitor's own availability window.

### 5. Visitor meets same faculty at most once

\[
\sum_{t \in \mathcal{T}} y_{sft} \le 1
\quad \forall s,f
\]

### 6. Excess visitors per faculty-time slot

\[
z_{ft} \ge \sum_{s \in \mathcal{S}} y_{sft} - 1
\quad \forall f,t
\]

This linearizes the "beyond one visitor" quantity used in the objective penalty.

### 7. Faculty overload indicator

\[
2q_f \ge
\sum_{s \in \mathcal{S}} \sum_{t \in \mathcal{T}} y_{sft}
- U_f + 2
\quad \forall f
\]

This activates \(q_f\) when total meetings exceed the soft threshold \(U_f - 2\).

### 8. Maximum group size per meeting

\[
\sum_{s \in \mathcal{S}} y_{sft} \le G
\quad \forall f,t
\]

### 9. Building occupancy indicators

\[
\sum_{f \in \mathcal{F}_A} y_{sft} \le A_{st}
\quad \forall s,t
\]

\[
\sum_{f \in \mathcal{F}_B} y_{sft} \le B_{st}
\quad \forall s,t
\]

### 10. Building movement constraints by mode

#### `Mode.BUILDING_A_FIRST`

\[
B_{s,t-1} + A_{st} \le 1
\quad \forall s,\; t>1
\]

Visitors may move from A to B but not return from B to A.

#### `Mode.BUILDING_B_FIRST`

\[
A_{s,t-1} + B_{st} \le 1
\quad \forall s,\; t>1
\]

Visitors may move from B to A but not return from A to B.

#### `Mode.NO_OFFSET`

\[
A_{s,t-1} + B_{st} \le 1
\quad \forall s,\; t>1
\]

\[
B_{s,t-1} + A_{st} \le 1
\quad \forall s,\; t>1
\]

Both directions require an intervening empty slot, enforcing travel via break.

### 11. Visitor break requirement

Applied when mode is `NO_OFFSET` or `enforce_breaks=True`:

\[
\sum_{f \in \mathcal{F}} \sum_{t \in \mathcal{B}} y_{sft}
\le |\mathcal{B}| - 1
\quad \forall s
\]

Each visitor must have at least one break during the configured break window.

### 12. Faculty break variables and requirement

Applied when mode is `NO_OFFSET` or `enforce_breaks=True`:

\[
\sum_{s \in \mathcal{S}} y_{sft} \le G(1-r_{ft})
\quad \forall f,\; t \in \mathcal{B}
\]

If \(r_{ft}=1\), faculty \(f\) has no meeting at break slot \(t\).

\[
\sum_{t \in \mathcal{B}} r_{ft} \ge 1
\quad \forall f \text{ with full-slot availability}
\]

Faculty with limited availability are exempt in the implementation.

### 13. Fixed unavailability for visitors

For visitor-specific availability restrictions, decision variables are fixed to zero:

\[
y_{sft} = 0
\quad \forall (s,t) \text{ not available to visitor } s,\; \forall f
\]

## Notes on Implementation

- The model is assembled in `Scheduler._build_model` and solved in `Scheduler._solve_model`.
- Feasibility checks and diagnostics are available through `has_feasible_solution` and `infeasibility_report`.
- Constraint activation depends on mode and `enforce_breaks` exactly as documented above.

## Example Solutions

The table below was generated by solving the worked dataset with:

- `mode=Mode.NO_OFFSET`
- `solver=Solver.HIGHS`
- `group_penalty=0.2`
- `min_visitors=2`
- `max_visitors=8`
- `min_faculty=1`
- `max_group=2`
- `enforce_breaks=True`

Solver metrics:
- total utility: `83.5`
- total excess-visitors penalty term: `0.2 * 9 = 1.8`
- faculty overload indicators: `0`
- objective value: `81.7`

### Solver-Generated Visitor Schedule

| Visitor | Slot 1 | Slot 2 | Slot 3 | Slot 4 |
| --- | --- | --- | --- | --- |
| Visitor 01 | Faculty C | Break | Break | Faculty A |
| Visitor 02 | Break | Faculty A | Break | Faculty B |
| Visitor 03 | Break | Break | Break | Faculty B |
| Visitor 04 | Break | Faculty A | Break | Faculty C |
| Visitor 05 | Break | Break | Faculty B | Break |
| Visitor 06 | Faculty B | Break | Break | Faculty A |
| Visitor 07 | Faculty C | Break | Faculty B | Break |
| Visitor 08 | Faculty B | Break | Faculty C | Break |
| Visitor 09 | Faculty A | Break | Break | Faculty C |
| Visitor 10 | Faculty A | Break | Faculty C | Break |

### Solver-Generated Faculty Load Summary

| Faculty | Total meetings | Slot 1 | Slot 2 | Slot 3 | Slot 4 |
| --- | ---: | --- | --- | --- | --- |
| Faculty A | 6 | 2 | 2 | 0 | 2 |
| Faculty B | 6 | 2 | 0 | 2 | 2 |
| Faculty C | 6 | 2 | 0 | 2 | 2 |
