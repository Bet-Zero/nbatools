# Contributing to nbatools

Thanks for your interest! Here's how to get started.

## Development Setup

Expected versions:

- Python 3.11 or newer. CI covers Python 3.11, 3.12, and 3.13.
- Node 22 for frontend work (`.nvmrc`). CI uses Node 22.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
npm --prefix frontend ci
pre-commit install
```

## Running Tests

Makefile targets provide deterministic test commands:

```bash
make doctor           # Lightweight local tool/setup check; does not run tests
make test-impacted    # Default for localized changes — tests affected by recent edits (testmon, serial)
make test-preflight   # Default for cross-cutting changes — all tests except slow (parallel)
make test-ci-fast     # Local equivalent of the PR CI fast gate
make test-smoke-all   # Stable + phase natural-query smoke suites
make test             # Full regression suite (parallel via xdist)
```

Makefile targets prefer `.venv/bin/python -m pytest` when `.venv` exists and
fall back to `python3 -m pytest` otherwise. You can still override `PYTHON` or
`PYTEST` for unusual environments.

### Command tiers

| Tier | Commands |
| --- | --- |
| Quick sanity | `make doctor`; `make docs-governance`; `make test-smoke-queries`; `make test-api` |
| Before commit | Quick sanity plus `npm --prefix frontend run lint`; `npm --prefix frontend test`; run focused pytest/domain targets for touched code |
| Before push | `npm --prefix frontend run build`; `npm --prefix frontend run lint`; `npm --prefix frontend test`; `make test-ci-fast` |
| Before release | `make test`; Raw QA public acceptance: `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice public_query_acceptance --run-id latest_public_query_acceptance --overwrite-run-id --fail-on-expectation-failure` |

### When to use each

| Command               | When                                                                                            |
| --------------------- | ----------------------------------------------------------------------------------------------- |
| `make doctor`         | Lightweight local setup check; verifies tools are present without running heavy tests           |
| `make test-impacted`  | Default for **localized** changes — small, leaf-level edits in a single module                  |
| `make test-preflight` | Default for **cross-cutting** changes — see "When to skip testmon" below                        |
| `make test-ci-fast`   | Match the PR `test-fast` gate locally without using testmon                                     |
| `make test-smoke-all` | Parser/query phase closure when the queue asks for both smoke suites                            |
| `make test`           | Before merging, in CI, or when you want full confidence                                         |

### Domain / subset targets

Run a specific subsystem slice when you know which area your change affects:

```bash
make test-unit        # Fast tests only — excludes slow and data-dependent tests
make test-impacted-parser # Impacted parser-marked tests only
make test-impacted-query  # Impacted query-marked tests only
make test-parser      # Parsing helpers, boolean parser, entity resolution
make test-query       # Natural query routing, intent detection, orchestration
make test-engine      # Core command computation, metrics, records, streaks, pipeline
make test-api         # HTTP API layer
make test-output      # Formatting, result contracts, export
```

These do **not** use testmon — they always run every test with the given marker.

### Marker reference

| Marker       | Purpose                                                        |
| ------------ | -------------------------------------------------------------- |
| `slow`       | Long-running tests. Deselect with `-m "not slow"`.             |
| `needs_data` | Requires local CSV data. Auto-skipped when data is missing.    |
| `parser`     | Pure parsing, entity resolution, boolean query parsing.        |
| `query`      | Natural query routing, intent detection, orchestration.        |
| `engine`     | Core command computation, metrics, records, streaks, pipeline. |
| `api`        | HTTP API layer tests.                                          |
| `output`     | Formatting, result contracts, export.                          |

### Testmon + marker interaction

`pytest --testmon -m parser -n0` runs only _impacted_ tests that are _also_ marked `parser`.
This is an **intersection** — it gives fewer tests than either flag alone.
Use this when you want the fastest possible feedback on a specific subsystem.

The domain targets (`make test-parser`, etc.) deliberately do **not** combine with
`--testmon`, so they always run the full subsystem slice.

### When to skip testmon

`make test-impacted` runs serial (`-n0`). When testmon selects a large number of tests, it costs more wall time than `make test-preflight` running in parallel. Skip `test-impacted` and use `make test-preflight` instead when **any** of these apply:

- The diff touches a high fan-in module: `src/nbatools/query_service.py`, `src/nbatools/commands/natural_query.py`, parser core, the API layer, or shared fixtures/conftest files.
- The diff exceeds ~50 lines in a single `src/` file.
- A previous `test-impacted` run on the same change selected more than ~300 tests, or visibly stalls past ~2 minutes without finishing.
- Data files, environment variables, or dynamically loaded modules changed (testmon does not track these).

For tight iteration on a high fan-in change, use a domain slice (`make test-query`, `make test-api`, `make test-parser`, etc.) first — these run the whole slice in parallel without testmon — then run `make test-preflight` once before finishing.

### Testmon limitations

`pytest-testmon` tracks file-level dependencies, not semantic ones.
It may miss tests affected by:

- changes in dynamic imports or monkey-patching
- changes in data files or fixtures loaded at runtime
- environment variable changes

When in doubt, run `make test`.

### Parser examples sweep

Run the full parser examples audit with:

```bash
make parser-examples-sweep
```

This writes ignored artifacts under `outputs/parser_examples_full_sweep/`.
Sweep-only queue items should run the sweep plus the smoke targets named by the
queue; they do not need `make test-impacted` unless code changed.

## Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.
Pre-commit hooks run automatically, or you can run manually:

```bash
ruff check src/ tests/ tools/
ruff format src/ tests/ tools/
```

## Continuous Integration

CI runs on GitHub Actions (`.github/workflows/ci.yml`).

### What runs when

| Trigger                      | Lint | Docs governance | Frontend install/audit/build/lint/test | `make test-unit` | `make test` |
| ---------------------------- | ---- | --------------- | --------------------------------------- | ---------------- | ----------- |
| Pull request                 | ✓    | ✓               | ✓                                       | ✓                |             |
| Push to `main`               | ✓    | ✓               | ✓                                       | ✓                | ✓           |
| Nightly schedule (06:00 UTC) | ✓    | ✓               | ✓                                       | ✓                | ✓           |
| Manual (`workflow_dispatch`) | ✓    | ✓               | ✓                                       | ✓                | ✓           |

- **`docs-governance`** (`make docs-governance`): Verifies durable-doc and working/archive policy checks.
- **`frontend`**: Runs `npm --prefix frontend ci`, fails on any low-or-higher
  npm advisory, then runs build, lint, and test.
- **`test-fast`** (`make test-unit`): Excludes `slow` and `needs_data` tests. Runs in parallel across Python 3.11/3.12/3.13. Provides fast feedback on every trigger.
- **`test-full`** (`make test`): Full regression suite in parallel. Runs on main push, nightly, and manual dispatch. Skipped on PRs to keep feedback fast.

### Caching

CI caches pip dependencies via `actions/setup-python`'s built-in `cache: pip` option. This avoids re-downloading packages on each run.

**pytest-testmon** is intentionally **not cached in CI**. Testmon is a local development tool (`make test-impacted`) — it tracks file-level dependencies across runs in a developer's working tree. In CI, each run starts from a clean checkout and the testmon database would rarely provide meaningful speedup. The fast CI path uses `make test-unit` (marker-based exclusion, parallel execution) instead.

### `needs_data` tests in CI

Tests marked `@pytest.mark.needs_data` auto-skip when `data/raw/` is absent. Since raw data is gitignored, these tests are effectively skipped in CI. They run only in local environments that have pulled NBA data.

## Pull Requests

1. Fork the repo and create a feature branch.
2. Make your changes with clear commit messages.
3. Ensure `pytest` and `ruff check` pass.
4. Open a PR with a description of what changed and why.
