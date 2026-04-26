# ── Test commands ──────────────────────────────────────────────────
#
# Deterministic targets for running the test suite.
# See CONTRIBUTING.md for when to use each.

.PHONY: test test-impacted test-impacted-parser test-impacted-query
.PHONY: test-preflight test-unit test-ci-fast
.PHONY: test-parser test-query test-engine test-api test-output
.PHONY: test-smoke-queries test-phase-smoke test-smoke-all
.PHONY: parser-examples-sweep

PYTHON ?= python
PYTEST ?= pytest

## Full regression suite (parallel via xdist).
## Use before merging, in CI, or when you want complete confidence.
test:
	$(PYTEST)

## Impacted tests only (pytest-testmon, serial).
## Fast feedback during development — runs only tests whose
## dependencies changed since the last recorded run.
## Limitations: testmon tracks file-level changes, not semantic ones.
## It may miss tests affected by changes in dynamic imports,
## monkey-patching, or data files.  When in doubt, run `make test`.
test-impacted:
	$(PYTEST) --testmon -n0

## Impacted parser tests only (testmon ∩ parser marker, serial).
## Use for tight parser iteration before the full parser slice.
test-impacted-parser:
	$(PYTEST) --testmon -m parser -n0

## Impacted natural-query tests only (testmon ∩ query marker, serial).
## Use for tight routing iteration before the full query slice.
test-impacted-query:
	$(PYTEST) --testmon -m query -n0

## Broader confidence run before finishing a task.
## Runs all tests except slow-marked ones (parallel via xdist).
## Broader than test-unit (includes needs_data tests that run locally)
## but cheaper than the full suite (skips slow tests).
## Does not use testmon — deterministic in all environments.
test-preflight:
	$(PYTEST) -m "not slow"

# ── Domain / subset targets ───────────────────────────────────────
#
# Use these to run a specific slice when you know which subsystem
# your change affects.  They do NOT use --testmon — they run every
# test with the given marker, regardless of whether files changed.

## Fast tests only — excludes slow and data-dependent tests.
test-unit:
	$(PYTEST) -m "not needs_data and not slow"

## Local equivalent of the PR CI fast test gate.
test-ci-fast: test-unit

## Parsing helpers, boolean parser, entity resolution.
test-parser:
	$(PYTEST) -m parser

## Natural query routing, intent detection, orchestration.
test-query:
	$(PYTEST) -m query

## Core command computation, metrics, records, streaks, pipeline.
test-engine:
	$(PYTEST) -m engine

## HTTP API layer.
test-api:
	$(PYTEST) -m api -n0

## Formatting, result contracts, export.
test-output:
	$(PYTEST) -m output

## Stable natural-query smoke checks through the real CLI and API paths.
test-smoke-queries:
	$(PYTEST) tests/test_query_smoke_stable.py -n0

## Phase-focused natural-query smoke checks for active parser/query work.
test-phase-smoke:
	$(PYTEST) tests/test_query_smoke_phase.py -n0

## Both smoke suites used by parser/query phase closure items.
test-smoke-all: test-smoke-queries test-phase-smoke

## Full parser examples audit; writes ignored artifacts under outputs/.
parser-examples-sweep:
	$(PYTHON) tools/parser_examples_full_sweep.py
