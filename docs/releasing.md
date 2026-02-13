# Releasing to PyPI

This project uses automated, tag-driven releases via GitHub Actions with a
TestPyPI gate and smoke test before PyPI publish.

Workflow file:

- `.github/workflows/release.yml`

## Release Checklist (Quick Reference)

| Stage | Check | Command / Action |
| --- | --- | --- |
| Pre-flight | On `main`, clean working tree | `git checkout main && git pull origin main && git status` |
| Pre-flight | Version/changelog updated | Verify `pyproject.toml` and `CHANGELOG.md` |
| Pre-flight | Tests pass locally | `pytest -q` |
| Trigger (tag path) | Create and push tag | `git tag -a vX.Y.Z -m "Release X.Y.Z"` then `git push origin vX.Y.Z` |
| Trigger (manual fallback) | Run workflow manually | GitHub Actions → `Release` → Run workflow (`target=pypi`, `version=X.Y.Z`) |
| Verification | Confirm tag exists remotely | `git ls-remote --tags origin | grep vX.Y.Z` |
| Verification | Confirm workflow completed | Check `Release` workflow run in GitHub Actions |
| Verification | Confirm install/version | `python -m pip install --upgrade grad-visitor-scheduler` and `python -c "import grad_visit_scheduler as gvs; print(gvs.__version__)"` |

## Release Pipeline (Current Behavior)

Trigger options:

- Push a version tag that matches `v*` (for example `v0.2.0`)
- Run manually from GitHub Actions (`workflow_dispatch`)

Pipeline stages:

1. Run tests (`pytest -q`)
2. Build package artifacts (`sdist` + `wheel`)
3. Validate metadata (`twine check`)
4. Publish artifacts to TestPyPI
5. Smoke install package from TestPyPI
6. Publish the same artifacts to PyPI

## One-Time Setup: Trusted Publishing

No PyPI API token is required. Publishing uses GitHub OIDC.

Configure Trusted Publisher in both:

- [PyPI](https://pypi.org/)
- [TestPyPI](https://test.pypi.org/)

For each index, set:

- Owner: `dowlinglab`
- Repository: `grad-visit-scheduler`
- Workflow: `release.yml`
- Environment: leave empty (unless you later add a GitHub Environment gate)

## Standard Release (Recommended)

1. Ensure `pyproject.toml` version is updated (for example `0.2.0`).
2. Update `CHANGELOG.md`.
3. Merge release changes to `main`.
4. Create and push tag:

```bash
git tag v0.2.0
git push origin v0.2.0
```

5. Open GitHub Actions and monitor `Release` workflow.

## Manual Release Runs (`workflow_dispatch`)

GitHub Actions → `Release` → `Run workflow`

Inputs:

- `target=testpypi`
  - Runs build/test/check + TestPyPI publish + smoke install
  - Stops before PyPI publish
- `target=pypi`
  - Runs full pipeline including PyPI publish
- `version` (optional)
  - Used to pin smoke install (e.g. `0.2.1` or `v0.2.1`)
  - If omitted, smoke install uses latest package visible on TestPyPI

## Verifying a Published Release

PyPI install check:

```bash
python -m pip install --upgrade grad-visitor-scheduler
python -c "import grad_visit_scheduler as gvs; print(gvs.__version__)"
```

TestPyPI install check:

```bash
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple grad-visitor-scheduler
python -c "import grad_visit_scheduler as gvs; print(gvs.__version__)"
```

## Common Failure Modes

- Trusted Publisher mismatch (`invalid-publisher`/auth errors):
  - Verify owner/repo/workflow filename exactly match configuration.
- Smoke install cannot find version on TestPyPI:
  - Wait a minute and rerun; index propagation can lag.
  - Confirm version in `pyproject.toml` matches tag.
- `File already exists` on publish:
  - That version is already uploaded; bump version and retag.
- Tag exists but no `on: push` release workflow appears:
  - Confirm tag exists on remote:
    `git ls-remote --tags origin | grep vX.Y.Z`
  - Use manual workflow dispatch on `main` as deterministic fallback:
    `target=pypi`, `version=X.Y.Z`.
- Build/test failures:
  - Release pipeline is intentionally blocked until tests/build succeed.

## Notes for Future You

- Package name on index: `grad-visitor-scheduler`
- Import name in Python: `grad_visit_scheduler`
- Current release trigger is **tag-first**; no GitHub Release object is required.
