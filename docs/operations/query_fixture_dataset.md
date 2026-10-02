# Query Fixture Dataset

## Purpose

A small, committed, synthetic NBA dataset that lets *behavioural* query tests run
everywhere — including CI — instead of skipping wherever the real pinned
generation is absent.

- Generator: `tools/generate_query_fixture.py`
- Fixture: `qa/fixtures/query_engine_sample/`
- Contract guard: `tests/test_query_fixture_contract.py`
- Regenerate: `make query-fixture` · Verify: `make query-fixture-check`

## The problem it solves

1036 of 4413 tests carried `needs_data` and skipped wherever the local dataset
was missing. GitHub CI never carries that dataset, so those tests had never run
on CI infrastructure on any trigger. Among them was all of
`tests/test_filter_execution_integrity.py` — the suite that guards the invariant
that a displayed filter badge corresponds to filtering that actually ran, which
is the single highest-value trust check in the repository.

That suite now runs on every trigger against this fixture.

## What the fixture is and is not for

This dataset is **synthetic**. Every number in it is invented. That bounds its
use, and the boundary is not a matter of taste.

| | Marker | Reads | Example assertion |
| --- | --- | --- | --- |
| **Behavioural** | `fixture_data` | this fixture | "a filter either changes the answer or is refused" |
| **Value** | `needs_data` | the real pinned generation | "Jokić averaged 26.4 points in 2023-24" |

A behavioural assertion holds against any internally consistent dataset, so it
can run anywhere. A value assertion cannot: pointing it at synthetic data would
not make it pass, it would make it **wrong**.

The two markers are mutually exclusive. `tests/conftest.py` asserts no single
test carries both, and `test_no_test_carries_both_data_markers` asserts no module
applies both.

## The vacuous-pass trap

This is the thing to understand before changing anything here.

`assert_filter_applied_or_refused` returns early when the filtered query is
refused — it never consults the control:

```text
filtered refused  ->  assert no badge displayed  ->  return
filtered answered ->  control must be ok+populated  ->  compare fingerprints
```

Most filter pairs in the integrity suite *expect* a refusal. So a fixture too
thin to answer the **control** queries makes every test in that suite pass while
comparing nothing — every query refuses for want of data, every assertion is
satisfied, and the guard becomes decorative. That is strictly worse than the
honest skip it replaced, because a green check is read as evidence.

`tests/test_query_fixture_contract.py` exists to make that impossible. It asserts
every control query returns a populated `ok` answer against the fixture.

**If a control-query test fails, do not weaken it.** Extend the fixture until the
control answers again. A refusing control means the filter assertion it backs has
silently stopped comparing anything.

## What the fixture contains

Derived deterministically from the seed at the top of the generator
(`RANDOM_SEED`), so the same input always produces byte-identical CSVs.

| Dimension | Value |
| --- | --- |
| Teams | 6 — real team ids, both conferences, two in the Pacific division |
| Players | 36 — 6 per team, spanning every position group the filter resolves |
| Seasons | 2023-24, 2024-25, 2025-26 |
| Games | 180 per season (double round robin ×6) — 60 per team |
| Postseason | one 6-game series in 2025-26 |
| Datasets | 56 CSV files, raw and processed |
| Size | ~2.7 MB on disk, ~0.3 MB compressed |

Internal consistency is a property of the generator, not of hand-editing: team
box scores are **summed from** their player lines, rest days are derived from
each team's own ordered game dates, and standings are derived from results.
`test_team_totals_equal_the_sum_of_their_player_lines` proves the emitted CSVs
still agree.

### Constraints that are not arbitrary

Four fixture properties exist because the engine requires them. Changing them
breaks the fixture in ways that are not obvious from the diff.

- **Season coverage must include `LATEST_REGULAR_SEASON` / `LATEST_PLAYOFF_SEASON`.**
  An unanchored query (`Lakers vs Celtics record`, `Lakers playoff history`)
  defaults to the latest season. Without it those controls refuse and stop being
  baselines.
- **Player names must be the engine's canonical forms**, diacritics included —
  `Nikola Jokić`, `Luka Dončić`, `Kristaps Porziņģis`. `apply_base_filters`
  matches `player_name` exactly against whatever entity resolution produced, so
  `Nikola Jokic` matches nothing.
- **No seed name may resolve to a different player.** The generator refuses to
  build if one does. Two real collisions were found and removed:
  `Karl-Anthony Towns` resolves to `Carmelo Anthony`, and `Nikola Jovic` resolves
  to `Nikola Jokić`. A fixture containing either would let one player's rows
  answer another player's question.
- **Seasons must be long enough for documented minimums.** Tests query
  `at least 50 games`; a 20-game season made those two tests fail for want of
  data rather than for behaviour.

## Changing the fixture

1. Edit the seed in `tools/generate_query_fixture.py` — not the CSVs.
2. `make query-fixture`
3. `pytest tests/test_query_fixture_contract.py tests/test_filter_execution_integrity.py`
4. Commit the generator change and the regenerated CSVs together.

`make docs-governance` runs `make query-fixture-check`, so a hand-edited or
stale fixture fails CI. The generator removes files it no longer produces, so a
changed seed cannot leave orphans behind that no pipeline would have emitted.

## Relationship to the real dataset

This fixture does not replace the real pinned generation and does not reduce the
need for it. Raw QA, the filter execution sweep, and every value-asserting test
still require real data, and the deployed application still reads an immutable
R2 generation.

What the fixture changes is that the behavioural half of the trust surface no
longer depends on a dataset that CI does not have.

## The real dataset still runs, now automatically

`.github/workflows/data-backed-validation.yml` runs the Raw QA corpus, the
filter execution sweep and the `needs_data` suite against the immutable R2
generation the deployed application reads — nightly and on demand. Those gates
had previously only ever run locally, on one machine, undated and unretained.

The `needs_data` skip check asks the *configured data source* rather than the
local filesystem, so those tests are runnable under `DATA_SOURCE=r2`. Checking
only the local path would have made that workflow skip all ~1000 of them and
report a green run having verified nothing.

See also:

- [`query_validation_map.md`](query_validation_map.md) — which validation layer
  answers which question
- [`filter_execution_sweep.md`](filter_execution_sweep.md) — the data-backed
  sweep this fixture's tests share an evidence contract with
