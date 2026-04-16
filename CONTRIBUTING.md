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
make test             # Full regression suite (parallel via xdist)
make test-impacted    # Only tests affected by recent code changes (pytest-testmon, serial)
make test-preflight   # All tests except slow — broad confidence before finishing a task
```

You can still invoke `pytest` directly with any flags you like.

### When to use each

| Command               | When                                                                |
| --------------------- | ------------------------------------------------------------------- |
| `make test-impacted`  | During active development for fast feedback                         |
| `make test`           | Before merging, in CI, or when you want full confidence             |
| `make test-preflight` | Before concluding a feature/fix — broad coverage without slow tests |

### Domain / subset targets

Run a specific subsystem slice when you know which area your change affects:

```bash
make test-unit        # Fast tests only — excludes slow and data-dependent tests
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

## Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.
Pre-commit hooks run automatically, or you can run manually:

```bash
ruff check src/ tests/
ruff format src/ tests/
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
