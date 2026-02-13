# Changelog

All notable changes to this project will be documented in this file.

This project follows a simple Keep a Changelog style and uses semantic versioning.

## [Unreleased]

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

## [0.2.0] - TBD

### Planned
- Promote current Unreleased changes into this release section when cutting the release.
