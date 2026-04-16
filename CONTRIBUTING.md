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

Three Makefile targets provide deterministic test commands:

```bash
make test             # Full regression suite (parallel via xdist)
make test-impacted    # Only tests affected by recent code changes (pytest-testmon, serial)
make test-preflight   # Impacted tests first, then full suite — run before finishing a task
```

You can still invoke `pytest` directly with any flags you like.

### When to use each

| Command               | When                                                                                          |
| --------------------- | --------------------------------------------------------------------------------------------- |
| `make test-impacted`  | During active development for fast feedback                                                   |
| `make test`           | Before merging, in CI, or when you want full confidence                                       |
| `make test-preflight` | Before concluding a feature/fix — catches impacted regressions fast, then verifies everything |

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

## Pull Requests

1. Fork the repo and create a feature branch.
2. Make your changes with clear commit messages.
3. Ensure `pytest` and `ruff check` pass.
4. Open a PR with a description of what changed and why.
