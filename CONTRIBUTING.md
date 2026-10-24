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
make test-preflight   # Broad coverage route — all tests except slow (parallel)
make test-ci-fast     # Local equivalent of the PR CI fast gate
make test-smoke-all   # Stable + phase natural-query smoke suites
make test             # Full regression suite (parallel via xdist)
```

Makefile targets prefer `.venv/bin/python -m pytest` when `.venv` exists and
fall back to `python3 -m pytest` otherwise. You can still override `PYTHON` or
`PYTEST` for unusual environments.

The application-command tiers below apply to affected behavior and risk, not diff
size or every receipt edit. Follow AGENTS.md's verification ownership and reuse
rules: focused author checks, existing CI for standard checks, independent judgment
where required, lead confirmation of applicability and resolved findings. The narrow planning-document CI path
under **Continuous Integration** preserves governance and policy checking.

### Command tiers

| Tier | Commands |
| --- | --- |
| Setup when needed | `make doctor` verifies local tools without running tests |
| While editing / before commit | Focused reproduction and relevant pytest/domain checks; docs changes: `make docs-governance` and `git diff --check` |
| Before merge | Applicable blocking CI and risk/acceptance coverage; fill only missing required coverage through an existing suitable route. Frontend build/lint/tests may be supplied by CI |
| Before release | Full regression and Raw QA public acceptance remain required: `make test`; `.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --slice public_query_acceptance --run-id latest_public_query_acceptance --overwrite-run-id --fail-on-expectation-failure`. Reuse only applicable successful evidence under AGENTS; preserve release/exact-candidate gates |

### When to use each

| Command               | When                                                                                            |
| --------------------- | ----------------------------------------------------------------------------------------------- |
| `make doctor`         | Lightweight local setup check; verifies tools are present without running heavy tests           |
| `make test-impacted`  | Default for **localized** changes — small, leaf-level edits in a single module                  |
| `make test-preflight` | Broad coverage route for cross-cutting risk; equivalent hosted evidence can satisfy it          |
| `make test-ci-fast`   | Local PR fast-gate route when needed; no mandatory duplicate of applicable CI                    |
| `make test-smoke-all` | Parser/query phase closure when the queue asks for both smoke suites                            |
| `make test`           | Full regression when required by affected risk or release; applicable hosted results may supply it |

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

`make test-impacted` runs serial (`-n0`) and can overselect. Prefer a focused/domain
slice while editing and broader coverage on the stable candidate when risk warrants it:

- The diff touches a high fan-in module: `src/nbatools/query_service.py`, `src/nbatools/commands/natural_query.py`, parser core, the API layer, or shared fixtures/conftest files.
- A previous `test-impacted` run overselects or makes no useful progress after 60 seconds.
- Data files, environment variables, or dynamically loaded modules changed (testmon does not track these).

For high fan-in integration, establish broad coverage equivalent to preflight/full
under AGENTS. Compare selected tests, configuration, relevant code/dependencies,
data generation and conditions; PR fast CI excludes data/slow tests and is not
automatically equivalent. Fill missing required pre-merge coverage once; do not
defer it to main/nightly. Freeze the candidate in isolated state before costly
validation/final review; do not move that checkout while it runs.

### Testmon limitations

`pytest-testmon` tracks file-level dependencies, not semantic ones.
It may miss tests affected by:

- changes in dynamic imports or monkey-patching
- changes in data files or fixtures loaded at runtime
- environment variable changes

Resolve uncertainty about affected behavior and coverage, then run the missing
checks; uncertainty alone is not a reason to repeat all accepted verification.

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

| Trigger                      | Lint | Docs governance | Frontend verify (build/lint/test) | Frontend security (shipped deps) | Frontend security (dev tree) | `make test-unit` | `make test` |
| ---------------------------- | ---- | --------------- | --------------------------------- | -------------------------------- | ---------------------------- | ---------------- | ----------- |
| Pull request                 | ✓    | ✓               | Impact                            | ✓                                | ✓ (reports)                  | Impact           |             |
| Push to `main`               | ✓    | ✓               | Impact                            | ✓                                | ✓ (reports)                  |                  | Impact      |
| Nightly schedule (06:00 UTC) | ✓    | ✓               | ✓                                 | ✓                                | ✓ (reports)                  |                  | ✓           |
| Manual (`workflow_dispatch`) | ✓    | ✓               | ✓                                 | ✓                                | ✓ (reports)                  |                  | ✓           |

**Impact** means all changes except an exclusively non-executable, regular-file
diff of `AGENTS.md`, `ROADMAP.md` and/or
`working/nba-tools-completion-program/README.md`. These are reviewed instructions
and handoffs, not runtime/build inputs. Apply AGENTS.md's review criteria: material
meaning/authority/verification-policy changes need independent review; ordinary
prose/cosmetic edits do not acquire a separate review gate just from their path;
a Markdown suffix alone does not qualify. Root `README.md` is packaging metadata;
other docs, tests/helpers, generated inputs, dependencies, configuration and the
selection mechanism itself conservatively select application checks.

Every run also executes `change-scope`: Node syntax, controlled Git-history tests,
CI policy and documentation-governance tests, without installing the application.
It compares the entire PR base/head or main before/after range, never just the
receipt commit. Missing/shallow/non-ancestor history selects all application jobs.
A failed policy/scope job fails CI and its missing output also selects those jobs.
The summary explains selection; unselected jobs remain visibly skipped, not
reported as executed passes. There are no workflow-level path filters that leave
required statuses waiting. Relevant numerical/data acceptance remains separately
required under AGENTS; this selector does not certify or reuse an NBA result.

The selector and workflow must receive independent review when changed. Before
reusing other evidence, the PR must retain its original revision and state why
relevant code, configuration, dependencies, data generation and environment still
apply; a documentation descendant is not a new exact-revision execution.

- **`docs-governance`** (`make docs-governance`): Verifies the generated
  repository inventory plus durable-doc and working/archive policy checks.
  After changing authoritative routes, result reasons/types, dataset specs, or
  Raw QA registries, run `make repository-inventory` to regenerate
  `contracts/repository_inventory.json`; `make repository-inventory-check`
  verifies it without writing.
- **`frontend-verify`**: Runs `npm --prefix frontend ci`, then build, lint, and
  test. This is the *code* verdict — does the frontend build and pass its
  tests?
- **`frontend-security`**: Runs `npm --prefix frontend ci`, then fails on any
  low-or-higher npm advisory in the **shipped** tree via
  `npm --prefix frontend audit --omit=dev --audit-level=low`. This is the
  *dependency* verdict for code that reaches a visitor's browser. Strict and
  blocking.
- **`frontend-security-dev`**: The same audit across the **whole** tree,
  development dependencies included, with `continue-on-error: true`. It reports
  advisories in the toolchain — the test runner, linter, bundler — which are
  worth fixing but cannot reach anyone using the app.

  All three jobs are independent and none waits on another. They fail for
  unrelated reasons: an advisory published upstream overnight says nothing
  about whether your code compiles, so it must not hide the build/lint/test
  result. The nightly run re-audits `main`, so advisories published after a
  lockfile lands are still caught.

  **Why the audit is split by scope (CI-SEC-01).** Three development-only
  advisories between 2026-08 and 2026-09 each held CI red for weeks with
  nothing wrong in this repository. Scoping the gate to shipped dependencies
  keeps a real security verdict while removing a recurring false alarm; the
  whole-tree audit still reports so nothing is hidden. This is a judgement for
  a solo repository with no CI secrets — a project with deploy credentials in
  CI should weigh a compromised build tool more heavily.
  `tests/test_ci_workflow_policy.py` guards the whole design, including that
  exactly one audit verdict can fail the workflow.
- **`test-fast`** (`make test-unit`): Excludes `slow` and `needs_data` tests. Runs across Python 3.11/3.12/3.13 on applicable PRs.
- **`test-full`** (`make test`): Same installation/configuration and all tests, including the fast subset. Runs across all three versions on applicable main pushes and every nightly/manual run. It replaces the duplicate fast matrix on those triggers; PRs retain fast feedback.

### A red `frontend-security` is policy-blocking, not merge-blocking

Three claims that are easy to conflate:

1. **Workflow-failing** — the job fails and the run goes red. *True.*
2. **Policy-blocking** — project policy says it must be green before merge.
   *True.* A dependency change needs a clean security verdict, and a red
   result must not be ignored or bypassed.
3. **Technically merge-blocking** — GitHub refuses the merge. *Not currently
   true.* No branch protection rule or repository ruleset names this check as
   required, so nothing mechanically stops a merge.

So the honest summary is: **policy-blocking and workflow-failing, but not
currently enforced as a required GitHub merge check.** Fix the dependency tree
rather than softening the check. Whether to configure required-check
enforcement is a separate governance decision, tracked as **CI-GOV-01** in
`working/nba-tools-completion-program/README.md`.

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
