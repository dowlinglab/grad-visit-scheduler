# Changelog

All notable changes to this project will be documented in this file.

This project follows a simple *Keep a Changelog* style and uses semantic versioning.

## [Unreleased]

## [0.3.0] - 2026-02-13

### Added
- New generalized building movement interface via run-config `movement`:
  - `movement.policy` (`none`, `travel_time`, or `nonoverlap_time`),
  - `movement.phase_slot` for per-building staggered starts,
  - `movement.travel_slots` for pairwise inter-building lag constraints.
- Automatic lag derivation utility `compute_min_travel_lags(...)` for shifted/nonuniform building clocks.
- Support for one-building and 3+ building close-proximity schedules (no hard two-building requirement).
- New movement-focused docs page: `docs/movement.md`, with executable examples, result tables, and schedule visuals.
- New comparison script for generalized building configurations:
  - `scripts/run_building_configuration_examples.py`.
- New/expanded movement example configs and catalogs in `examples/`.
- New shifted-clock auto non-overlap example config:
  - `examples/config_shifted_nonoverlap_auto.yaml`.
- Public `Scheduler.current_solution()` accessor for retrieving the currently
  loaded feasible `SolutionResult` snapshot.
- Expanded movement hardening tests:
  - deterministic offset/duration sweep checks for auto lag sufficiency,
  - lag minimality/monotonicity checks,
  - 3-building shifted-clock overlap/infeasibility behavior checks,
  - dedicated example integration solve test.

### Changed
- `Scheduler` now treats movement config as the preferred interface; legacy `Mode` is compatibility-only.
- Mathematical formulation docs updated to reflect generalized movement model:
  - building phase constraints,
  - travel-time occupancy/lag constraints,
  - explicit Top-N no-good-cut equation section.
- Quickstart/API docs now cross-reference movement usage and updated model sections.
- Building-configuration examples now use the larger formulation dataset to better expose edge cases while remaining fast to solve.
- `Scheduler.schedule_visitors(...)` now returns `SolutionResult` on feasible
  solves and `None` when no feasible solution is found.
- Primary README/quickstart/scripts now use the modern single-solution flow
  (`sol = s.schedule_visitors(...)`) for plotting and DOCX export.
- Legacy mode migration guidance now explicitly documents mode-to-movement
  mappings and the break-behavior nuance for `NO_OFFSET`.
- Added shifted-clock safety warning for `movement.policy='none'`, plus auto
  non-overlap movement options (`nonoverlap_time` and `travel_slots: auto`).
- `slot2min(...)` now validates slot format and increasing time windows with
  explicit errors for malformed labels.
- Movement docs now include:
  - policy selection guide,
  - failure-modes diagnostics table with message-to-fix mapping,
  - direct reference to the dedicated shifted auto non-overlap example.

### Deprecated
- Explicit legacy `mode=...` scheduling interface now emits `FutureWarning` for all modes (`BUILDING_A_FIRST`, `BUILDING_B_FIRST`, and `NO_OFFSET`).
- Passing both `mode` and `movement` emits `FutureWarning` and ignores `mode`.
- Top-level `grad_visit_scheduler.export_visitor_docx(...)` remains available
  for compatibility and continues to emit `FutureWarning`; prefer
  `SolutionResult.export_visitor_docx(...)`.

## [0.2.1] - 2026-02-13

### Added
- Release checklist quick reference table in `docs/releasing.md` for streamlined release workflows.

### Changed
- Clarified Top-N workflow usage in `docs/quickstart.md` with reference to modern `SolutionSet`/`SolutionResult` interface.
- Enhanced `docs/releasing.md` with additional troubleshooting for tag-related release workflow issues.

## [0.2.0] - 2026-02-13

### Added
- Top-N schedule generation via no-good integer cuts (`schedule_visitors_top_n`).
- Rich solution objects (`SolutionResult`) and container (`SolutionSet`).
- Cross-solution summary tables and helper workflow (`SolutionSet.summarize`).
- Rank-aware visualization toggles and standardized comparison outputs.
- New top-N example script and notebook section.
- Expanded automated test suite with edge-case and branch-focused tests for:
  - solver state semantics after top-N exhaustion,
  - GUROBI IIS integration/error paths,
  - configuration validation and weight handling,
  - legacy warning wrappers and plotting/export helpers.
- Dedicated tests for module re-exports in `grad_visit_scheduler.plotting`.
- Automated release workflow for PyPI/TestPyPI via GitHub Actions:
  - tag-driven release trigger (`v*`),
  - TestPyPI publish and smoke-install gate before PyPI publish,
  - manual `workflow_dispatch` support (`target=testpypi|pypi`, optional `version`),
  - Trusted Publishing (OIDC, no API token secret).
- Dedicated release playbook documentation in `docs/releasing.md`.

### Changed
- Refactored visualization/export responsibilities toward `SolutionResult`.
- Scheduler plotting/export methods now act as legacy wrappers.
- Documentation expanded for top-N usage and solution review workflows.
- CI and coverage workflow hardened:
  - GitHub Actions test matrix on Python 3.10/3.11/3.12,
  - Codecov upload configured in CI (OIDC),
  - Coverage artifact generation (`coverage.xml`) standardized.
- Test quality improved from smoke checks to behavior-level assertions across plotting, DOCX export, and solver diagnostics.

### Deprecated
- `Scheduler.show_faculty_schedule(...)` in favor of `SolutionResult.plot_faculty_schedule(...)`.
- `Scheduler.show_visitor_schedule(...)` in favor of `SolutionResult.plot_visitor_schedule(...)`.
- `Scheduler.export_visitor_docx(...)` and top-level `export_visitor_docx(...)` in favor of `SolutionResult.export_visitor_docx(...)`.

### Notes
- Optional solver tests skip automatically when a solver backend is not installed.
- Current local/CI coverage target is now fully exercised (`100%` line coverage in package modules).

## [0.1.2] - 2026-02-11

### Added
- Expanded documentation and examples, including a Colab demo workflow.
- Added richer docs visuals (example figures, badges, and links).

### Changed
- Improved quickstart/formulation documentation and math explanations.
- Fixed plotting abbreviation behavior for names like `Visitor 01`.
- Polished README and docs wording/formatting.

## [0.1.1] - 2026-02-10

### Added
- Initial public package release from the generalized private scheduler codebase.

### Changed
- Finalized packaging metadata and dependencies for PyPI distribution.
- Updated project configuration and repository hygiene (`.gitignore`, setup readiness).
