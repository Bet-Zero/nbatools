# Contributing to nbatools

Thanks for your interest! Here's how to get started.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Running Tests

Makefile targets provide deterministic test commands:

```bash
make test-impacted    # Default: only tests affected by recent code changes (pytest-testmon, serial)
make test-ci-fast     # Local equivalent of the PR CI fast gate
make test-smoke-all   # Stable + phase natural-query smoke suites
make test             # Full regression suite (parallel via xdist)
make test-preflight   # All tests except slow — for broad, cross-cutting, or higher-risk changes only
```

You can still invoke `pytest` directly with any flags you like.
If your shell does not have the virtualenv first on `PATH`, pass tool paths
explicitly, for example `make PYTEST=.venv/bin/pytest test-smoke-all`.

### When to use each

| Command               | When                                                                                       |
| --------------------- | ------------------------------------------------------------------------------------------ |
| `make test-impacted`  | **Default** — during active development and as the normal finishing step for ordinary work |
| `make test-ci-fast`   | Match the PR `test-fast` gate locally without using testmon                         |
| `make test-smoke-all` | Parser/query phase closure when the queue asks for both smoke suites                |
| `make test`           | Before merging, in CI, or when you want full confidence                                    |
| `make test-preflight` | Broad, cross-cutting, or higher-risk changes only — not the default finishing step         |

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

### Testmon limitations

`pytest-testmon` tracks file-level dependencies, not semantic ones.
It may miss tests affected by:

- changes in dynamic imports or monkey-patching
- changes in data files or fixtures loaded at runtime
- environment variable changes

When in doubt, run `make test`.

`make test-impacted` is serial by design (`-n0`). When a shared file such as
`src/nbatools/commands/natural_query.py` changes, testmon can still select a
large number of tests, so pytest progress percentages may advance slowly. For
tight iteration, use `make test-impacted-parser` or `make test-impacted-query`
first, then run the full required target once before finishing.

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

| Trigger                      | Lint | `make test-unit` | `make test` |
| ---------------------------- | ---- | ---------------- | ----------- |
| Pull request                 | ✓    | ✓                |             |
| Push to `main`               | ✓    | ✓                | ✓           |
| Nightly schedule (06:00 UTC) | ✓    | ✓                | ✓           |
| Manual (`workflow_dispatch`) | ✓    | ✓                | ✓           |

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
