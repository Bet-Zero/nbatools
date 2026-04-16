# ── Test commands ──────────────────────────────────────────────────
#
# Three deterministic targets for running the test suite.
# See CONTRIBUTING.md for when to use each.

.PHONY: test test-impacted test-preflight

## Full regression suite (parallel via xdist).
## Use before merging, in CI, or when you want complete confidence.
test:
	pytest

## Impacted tests only (pytest-testmon, serial).
## Fast feedback during development — runs only tests whose
## dependencies changed since the last recorded run.
## Limitations: testmon tracks file-level changes, not semantic ones.
## It may miss tests affected by changes in dynamic imports,
## monkey-patching, or data files.  When in doubt, run `make test`.
test-impacted:
	pytest --testmon -n0

## Broader confidence run before finishing a task.
## Runs impacted tests first (fast fail), then the full suite.
test-preflight:
	pytest --testmon -n0
	pytest
