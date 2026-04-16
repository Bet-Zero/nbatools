# ── Test commands ──────────────────────────────────────────────────
#
# Deterministic targets for running the test suite.
# See CONTRIBUTING.md for when to use each.

.PHONY: test test-impacted test-preflight test-unit test-parser test-query test-engine test-api test-output

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

# ── Domain / subset targets ───────────────────────────────────────
#
# Use these to run a specific slice when you know which subsystem
# your change affects.  They do NOT use --testmon — they run every
# test with the given marker, regardless of whether files changed.

## Fast tests only — excludes slow and data-dependent tests.
test-unit:
	pytest -m "not needs_data and not slow"

## Parsing helpers, boolean parser, entity resolution.
test-parser:
	pytest -m parser

## Natural query routing, intent detection, orchestration.
test-query:
	pytest -m query

## Core command computation, metrics, records, streaks, pipeline.
test-engine:
	pytest -m engine

## HTTP API layer.
test-api:
	pytest -m api -n0

## Formatting, result contracts, export.
test-output:
	pytest -m output
