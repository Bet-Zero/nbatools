# Query Smoke Workflow

## Purpose

These smoke tests run real natural-language queries through the shipped CLI and API paths.

They answer a different question than parser, routing, API, or frontend tests: if a user types a representative query into the product right now, does the end-to-end query path still behave sanely?

They are intentionally lightweight and stable:

- real natural queries, not structured route fixtures
- route, query class, status, and envelope assertions
- no dependence on exact pretty-output text
- phase-specific assertions only where the current product behavior is part of the point

## Coverage

Stable regression smoke lives in `tests/test_query_smoke_stable.py` and covers a compact always-run set:

- `Jokic last 10`
- `top scorers this season`
- `Lakers vs Celtics all-time record`
- `how many Jokic games with 30+ points and 10+ rebounds since 2021`
- `Curry 5+ threes this season`

Phase-focused smoke lives in `tests/test_query_smoke_phase.py`.

Current Phase D and current parser-surface checks:

- `Celtics recently`
- `Tatum vs Knicks`
- `Jokic triple doubles`
- `best games Booker`
- `Lakers this season`

Current Phase E clutch checks:

- `Tatum clutch stats`
- `Lakers clutch record`
- `best clutch scorers`
- `late-game Brunson scoring`

The shared case lists and harness live in `tests/_query_smoke.py`.

## What The Harness Checks

CLI path:

- runs the real `nbatools-cli ask` command through Typer
- exports JSON so assertions use structured output instead of pretty-text formatting
- checks query text, route, query class, result status, and that the export has real sections or an honest `no_result` payload
- checks current clutch-warning notes in CLI metadata for the Phase E clutch queries

API path:

- posts the same natural queries to the real `/query` endpoint with `TestClient`
- checks the `QueryResponse` envelope shape
- checks route, query class, result status, confidence, intent, and alternates shape when present

## How To Run

Stable regression smoke:

```bash
make test-smoke-queries
```

Phase-focused smoke:

```bash
make test-phase-smoke
```

Single query while iterating:

```bash
pytest tests/test_query_smoke_stable.py -n0 -k jokic-last-10
pytest tests/test_query_smoke_phase.py -n0 -k clutch
```

These tests require local processed data and are marked `needs_data`.

## When To Run Them

- Run `make test-smoke-queries` after changes that affect real natural-query behavior and before closing a phase item.
- Run `make test-phase-smoke` when working the active parser/query-surface phase or a feature family that still has honest temporary behavior.
- Keep using the normal parser, query, engine, API, and frontend test suites for subsystem correctness. These smoke tests are product-sanity checks, not replacements.

## Adding New Queries

Add new stable queries only when they represent durable shipped behavior you want to protect every phase.

Add new phase queries to the appropriate phase tuple in `tests/_query_smoke.py`:

- `PHASE_D_QUERY_SMOKE_CASES`
- `PHASE_E_QUERY_SMOKE_CASES`

If a future phase starts, add a new phase tuple there and let `tests/test_query_smoke_phase.py` inherit it.

Keep assertions loose unless a stricter check is the behavior under test:

- prefer route, query class, status, intent, and alternates shape
- avoid exact pretty-output text
- if a feature is parser-detected but not fully executed yet, assert that temporary behavior honestly until the real filter ships
