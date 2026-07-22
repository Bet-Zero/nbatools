# ── Test commands ──────────────────────────────────────────────────
#
# Deterministic targets for running the test suite.
# See CONTRIBUTING.md for when to use each.

.PHONY: doctor
.PHONY: test test-impacted test-impacted-parser test-impacted-query
.PHONY: test-preflight test-unit test-ci-fast
.PHONY: test-parser test-query test-engine test-api test-output
.PHONY: test-smoke-queries test-phase-smoke test-smoke-all
.PHONY: parser-examples-sweep raw-query-answer-qa exploratory-query-review query-feedback-export
.PHONY: browser-release-review visual-qa-screenshots
.PHONY: repository-inventory repository-inventory-check docs-governance

PYTHON ?= $(shell if [ -x .venv/bin/python ]; then printf '%s' .venv/bin/python; elif command -v python3 >/dev/null 2>&1; then command -v python3; elif command -v python >/dev/null 2>&1; then command -v python; else printf '%s' python3; fi)
PYTEST ?= $(PYTHON) -m pytest
VISUAL_QA_BASE_URL ?= http://127.0.0.1:8000
VISUAL_QA_RUN_ID ?=
BROWSER_REVIEW_BASE_URL ?= http://127.0.0.1:8000
BROWSER_REVIEW_RUN_ID ?=

## Lightweight local setup check. Does not run tests.
doctor:
	@set -u; status=0; \
	echo "nbatools doctor"; \
	echo ""; \
	echo "Python"; \
	echo "  executable: $(PYTHON)"; \
	if $(PYTHON) --version >/dev/null 2>&1; then \
		echo "  version: $$($(PYTHON) --version 2>&1)"; \
	else \
		echo "  [fail] configured Python is not runnable"; status=1; \
	fi; \
	if [ -x .venv/bin/python ]; then \
		echo "  [ok] .venv present"; \
	else \
		echo "  [warn] .venv not found; using fallback Python"; \
	fi; \
	if $(PYTHON) -m pytest --version >/dev/null 2>&1; then \
		echo "  [ok] pytest available via $(PYTHON) -m pytest"; \
	else \
		echo "  [fail] pytest is not available via $(PYTHON) -m pytest"; status=1; \
	fi; \
	echo ""; \
	echo "Node"; \
	if command -v node >/dev/null 2>&1; then \
		echo "  node: $$(node --version)"; \
	else \
		echo "  [fail] node not found"; status=1; \
	fi; \
	if command -v npm >/dev/null 2>&1; then \
		echo "  npm: $$(npm --version)"; \
	else \
		echo "  [fail] npm not found"; status=1; \
	fi; \
	if [ -d frontend/node_modules ]; then \
		echo "  [ok] frontend/node_modules present"; \
	else \
		echo "  [warn] frontend/node_modules missing; run npm --prefix frontend ci"; \
	fi; \
	echo ""; \
	echo "Docs"; \
	if [ -f tools/check_docs_governance.py ]; then \
		echo "  [ok] docs governance script present"; \
	else \
		echo "  [fail] docs governance script missing"; status=1; \
	fi; \
	exit $$status

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

## Curated raw query answer QA harness; writes ignored artifacts under outputs/.
raw-query-answer-qa:
	$(PYTHON) tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml

## Input-only natural-query review snapshot; writes ignored artifacts under outputs/.
exploratory-query-review:
	$(PYTHON) tools/exploratory_query_review.py --input qa/exploratory_query_samples.yaml

## Input-only exploratory query slice review; pass SLICE=001_player_last_n.
exploratory-query-review-slice:
	$(PYTHON) tools/exploratory_query_review.py --slice $(SLICE)

## Read-only query feedback review export; writes ignored artifacts under outputs/.
query-feedback-export:
	$(PYTHON) tools/export_query_feedback.py

## Browser screenshot artifact capture for the 20-case /visual-qa corpus.
## Build the frontend and start the local API shell before running this target.
visual-qa-screenshots:
	npm --prefix frontend run qa:visual-screenshots -- --base-url "$(VISUAL_QA_BASE_URL)" $(if $(VISUAL_QA_RUN_ID),--run-id "$(VISUAL_QA_RUN_ID)")

browser-release-review:
	npm --prefix frontend run qa:browser-release-review -- --base-url "$(BROWSER_REVIEW_BASE_URL)" $(if $(BROWSER_REVIEW_RUN_ID),--run-id "$(BROWSER_REVIEW_RUN_ID)")

## Rewrite the deterministic inventory of authoritative repository surfaces.
repository-inventory:
	$(PYTHON) tools/generate_repository_inventory.py --write

## Fail when the committed repository inventory differs from authoritative sources.
repository-inventory-check:
	$(PYTHON) tools/generate_repository_inventory.py --check

## Durable-doc path and relative-link governance check.
docs-governance: repository-inventory-check
	$(PYTHON) tools/check_docs_governance.py
