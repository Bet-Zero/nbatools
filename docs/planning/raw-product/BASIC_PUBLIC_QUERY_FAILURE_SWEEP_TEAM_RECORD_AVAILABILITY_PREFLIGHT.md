# Basic Public Query Failure Sweep: Team Record Availability Preflight

Date: 2026-05-23

Scope: originally preflight only. Execution is now complete in
`return_packages/raw-product/BASIC_PUBLIC_QUERY_FAILURE_SWEEP_TEAM_RECORD_AVAILABILITY_RETURN_PACKAGE.md`.
The execution wave added narrow parser/query support for single-player
team-record presence, preserved the supported absence baseline, and guarded
compound or unresolved availability without broad fallback.

## 1. Goal

Investigate basic public query failures and near-misses from local usage,
focused on team-record player-availability variants.

The user-discovered query set:

- `Luka stats this season`
- `Lakers record without Luka`
- `Lakers record with Luka`
- `Lakers record with Reaves`
- `Lakers record with Reaves without Luka`
- `Lakers record without Luk`
- `Who had the most rebounds in a game this year?`

`Lakers record without Luka` is treated as the supported baseline. It is not a
failure.

## 2. Current Behavior Probes

Probe path:

```bash
.venv/bin/python - <<'PY'
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query
from nbatools.api_handlers import query_result_to_payload
PY
```

The probe executed each query through `execute_natural_query()` and
`query_result_to_payload()`, the same backend payload path consumed by the API
and UI.

CLI pretty-output spot checks were also run with `.venv/bin/nbatools-cli ask`
for the same query family to capture the visible answer subject and headline
values.

### Current Behavior Matrix

| Query | Route | Status / reason | Visible answer / primary row | Sections | `metadata.unsupported_filters` | Classification |
|---|---|---|---|---|---|---|
| `Luka stats this season` | `player_game_summary` | `ok` / null | Luka Dončić, 64 games, 43-21, 33.484 PPG, 7.734 RPG, 8.281 APG | `summary:1`, `by_season:1`, `game_log:64` | null | Supported and working |
| `Lakers record without Luka` | `team_record` | `ok` / null | Los Angeles Lakers, 18 games, 10-8, .556; caveat: record filtered to games without Luka Dončić | `summary:1`, `by_season:1`, `game_log:18` | null | Supported baseline and working |
| `Lakers record with Luka` | `player_game_summary` | `ok` / null | Luka Dončić, 64 games, 43-21, .672; player averages shown | `summary:1`, `by_season:1`, `game_log:64` | null | Wrong-scope / public copy issue for a team-record availability query |
| `Lakers record with Reaves` | `player_game_summary` | `ok` / null | Austin Reaves, 51 games, 36-15, .706; player averages shown | `summary:1`, `by_season:1`, `game_log:51` | null | Wrong-scope / public copy issue for a team-record availability query |
| `Lakers record with Reaves without Luka` | `player_game_summary` | `ok` / null | Austin Reaves, 10 games, 6-4, .600; `without_player=Luka Dončić` applied to player rows | `summary:1`, `by_season:1`, `game_log:10` | null | Unsupported compound availability currently returns a plausible wrong-scope answer |
| `Lakers record without Luk` | `team_record` | `ok` / null | Los Angeles Lakers, 82 games, 53-29, .646; no absence filter applied | `summary:1`, `by_season:1` | null | Typo / unresolved-player broad fallback; should not return full team record |
| `Who had the most rebounds in a game this year?` | `top_player_games` | `ok` / null | Leaderboard top row: Scottie Barnes, 25 rebounds, TOR vs GSW, 2025-12-28 | `leaderboard:10` | null | Supported and working |

Notes:

- The backend payloads above did not include `metadata.answer_phrase` for these
  team-record or player-summary responses. The visible answer wording here is
  taken from CLI pretty output and first-row structured data.
- `this year` currently resolves to the loaded current regular season,
  `2025-26`, for the top single-game rebounds query.
- The `Lakers record with Reaves without Luka` result is data-filtered at the
  player-summary grain, but it is not a `team_record` response and does not
  expose a compound team availability contract.

## 3. Current Intended Support

### Team Record Without Player

Supported.

Evidence:

- `docs/reference/current_state_guide.md` lists record without a specified
  player as supported team-record behavior.
- `docs/reference/query_catalog.md` documents without-player filters and states
  that they exclude games where the specified player played, clearing the
  player from entity detection so the query routes to the team path.
- `qa/raw_query_answer_corpus.yaml` includes supported without-player cases:
  `suns_without_booker_shorthand`, `bucks_without_giannis`,
  `knicks_without_brunson`, `lakers_without_lebron`, and
  `warriors_wins_without_curry`.
- `tests/test_ui_failure_coverage.py` includes execution coverage proving
  `Lakers record without LeBron` routes to `team_record`, returns `ok`, applies
  the `Without player` filter, and includes `game_log`.

The supported result shape is:

- `route=team_record`
- `result_status=ok`
- `result_reason=null`
- `metadata.without_player=<resolved player>`
- `metadata.applied_filters` includes
  `{"label":"Without player","value":<resolved player>,"kind":"player"}`
- sections include `summary`, `by_season`, and `game_log`

### Team Record With Player

Not currently documented as shipped team-record behavior.

Current parser behavior treats `with Luka` and `with Reaves` as a player entity
inside a player-summary route. That returns a record for the player's game rows
with the team filter applied, but the public subject is the player, not the
team-record availability slice the user asked for.

Data capability is available in principle:

- `player_game_stats` has player appearances by `game_id` and `team_id`.
- `load_player_games_for_seasons()` merges team `wl` from `team_game_stats`.
- A team-game result could be produced by intersecting team games with resolved
  player appearance game IDs for the same team.

Product support is not currently complete:

- `team_record.build_team_record_result()` accepts `without_player` but no
  `with_player` slot.
- There is no `metadata.with_player`, applied-filter label, caveat, or result
  contract for whole-game player presence team records.
- There are no raw QA cases or targeted tests for single-player `team record
  with PLAYER`.

Recommended boundary for the next execution wave:

- Promote single-player whole-game presence team records as supported because
  the data is already available and the user intent is basic public usage.
- Route `Lakers record with Luka` and `Lakers record with Reaves` to
  `team_record`, not `player_game_summary`.

### Compound Availability

Unsupported today.

Existing product boundary:

- `docs/reference/query_catalog.md` says multi-player availability record
  phrasing such as `Lakers record when LeBron and AD both play` is outside the
  current lineup/availability boundary and should return explicit
  unsupported/no-result.
- `qa/raw_query_answer_corpus.yaml` includes
  `lakers_lebron_ad_both_play`, expected as `team_record` /
  `no_result` / `filter_not_supported` with
  `metadata.unsupported_filters.0 == multi_player_availability`.
- `tests/test_ui_failure_coverage.py` covers `both play`, `both out`,
  `with LeBron and AD`, and `without LeBron and AD` as unsupported
  multi-player availability.

Coverage gap:

- `with Reaves without Luka` is not caught by the current multi-player
  availability boundary because it is one presence phrase plus one absence
  phrase. It currently routes to a player summary and returns a plausible
  wrong-scope answer.

Expected boundary until a dedicated contract exists:

- `route=team_record`
- `result_status=no_result`
- `result_reason=filter_not_supported`
- sections empty
- `metadata.unsupported_filters=["multi_player_availability"]`
- note mentions multi-player availability and no broad fallback

### Typo / Partial Player Names

Not supported as a broad fallback.

Current behavior for `Lakers record without Luk` is unsafe: the unresolved
absence fragment is dropped and the full Lakers record is returned.

Expected boundary:

- The parser should preserve that an availability filter was requested but the
  player could not be confidently resolved.
- The engine should return `no_result`, not an unfiltered `team_record`.
- Preferred shape:
  - `route=team_record`
  - `result_status=no_result`
  - `result_reason=ambiguous`
  - sections empty
  - metadata includes an entity-ambiguity or unresolved-filter payload with the
    raw fragment `Luk`
  - if candidate generation is available, candidate should include
    `Luka Dončić`

If the next wave chooses an unsupported-filter representation instead, it
should still avoid broad fallback and should expose a stable filter ID such as
`unresolved_without_player`.

### Top Single-Game Rebounds

Supported and working.

Evidence:

- `docs/reference/query_catalog.md` documents non-scoring single-game
  leaderboard variants.
- `qa/raw_query_answer_corpus.yaml` includes
  `What were the most rebounds in a game this season?` expected as
  `top_player_games`.
- `tests/test_natural_query_parser.py` covers
  `most rebounds in a game this season` and
  `most rebounds by a player in a game this season`.

The exact user query `Who had the most rebounds in a game this year?` is not the
same raw QA phrase, but the current route and result are correct.

## 4. Data Capability

| Capability | Current data support | Current product support | Notes |
|---|---|---|---|
| Single-team record without one player | Yes | Shipped | Implemented by `filter_without_player()` using `player_game_stats` appearance rows and `team_game_stats` team rows. |
| Single-team record with one player | Yes in principle | Not shipped as `team_record` | Requires a `with_player` slot/helper using the same game-id and team matching model in reverse. |
| Compound presence plus absence | Yes in principle for whole-game appearance filters | Not shipped | Needs explicit semantics, metadata, caveats, and tests before support. |
| Multi-player both-play / both-out records | Data can be derived in pieces | Explicitly unsupported | Existing boundary is correct and should be extended to mixed with/without phrasing. |
| Partial typo `Luk` | Resolver does not confidently resolve | Not supported | Should no-result/clarify rather than drop the requested filter. |
| On/off presence | Separate data contract exists | Separate `player_on_off` route | `team_player_on_off_summary` is stint/on-off style and must not be conflated with whole-game availability. |

## 5. Classification

| Query | Classification | Rationale |
|---|---|---|
| `Luka stats this season` | Supported and working | Player summary route and data are correct. |
| `Lakers record without Luka` | Supported and working | Baseline `team_record` absence filter works and includes team game log. |
| `Lakers record with Luka` | Supported intent, failing route/shape | Basic team availability intent is data-capable but currently shown as player summary. |
| `Lakers record with Reaves` | Supported intent, failing route/shape | Same as with-Luka. |
| `Lakers record with Reaves without Luka` | Unsupported compound availability should no-result cleanly | Current player-summary answer is plausible but outside the documented compound availability boundary. |
| `Lakers record without Luk` | Ambiguous/typo should no-result cleanly | Current behavior drops the absence filter and returns full team record. |
| `Who had the most rebounds in a game this year?` | Supported and working | Routes to `top_player_games` with `stat=reb`. |

## 6. Expected Behavior Targets

### Supported Presence Targets

For `Lakers record with Luka`:

- `route=team_record`
- `result_status=ok`
- `result_reason=null`
- `metadata.team="LAL"`
- `metadata.with_player="Luka Dončić"` or equivalent stable field
- `metadata.applied_filters` includes a player filter labeled `With player`
- sections: `summary`, `by_season`, `game_log`
- summary row: Lakers team row, 64 games, 43 wins, 21 losses, .672 win pct
- caveat: record filtered to games with Luka Dončić

For `Lakers record with Reaves`:

- `route=team_record`
- `result_status=ok`
- `result_reason=null`
- `metadata.team="LAL"`
- `metadata.with_player="Austin Reaves"`
- sections: `summary`, `by_season`, `game_log`
- summary row: Lakers team row, 51 games, 36 wins, 15 losses, .706 win pct
- caveat: record filtered to games with Austin Reaves

These targets intentionally use the same win/loss samples currently visible in
the player-summary responses, but change the route, subject, metadata, and
result shape to team-record semantics.

### Unsupported Compound Target

For `Lakers record with Reaves without Luka`:

- `route=team_record`
- `result_status=no_result`
- `result_reason=filter_not_supported`
- `metadata.team="LAL"`
- `metadata.unsupported_filters=["multi_player_availability"]`
- sections: empty
- note: multi-player availability filters are not supported with current data
  and no broad team record was returned

This should remain unsupported until the product approves compound
availability and adds result-contract coverage.

### Typo / Partial Target

For `Lakers record without Luk`:

- `route=team_record`
- `result_status=no_result`
- preferred `result_reason=ambiguous`
- sections: empty
- metadata preserves the unresolved availability fragment `Luk`
- if candidate metadata is emitted, include `Luka Dončić`

No acceptable target may return the full 82-game Lakers record.

## 7. Fix Plan

### Tests And Corpus Cases To Add

Raw QA corpus:

- `lakers_record_with_luka`
  - query: `Lakers record with Luka`
  - expected `team_record` / `ok`
  - expected shape `team_record`
  - expected sections `summary`, `game_log`
  - hard assertions: `result.sections.summary.0.games == 64`,
    `wins == 43`, `losses == 21`
  - expected filter: `With player = Luka Dončić`
- `lakers_record_with_reaves`
  - expected `team_record` / `ok`
  - hard assertions: `games == 51`, `wins == 36`, `losses == 15`
- `lakers_record_with_reaves_without_luka`
  - expected `team_record` / `no_result` / `filter_not_supported`
  - hard assertion:
    `result.metadata.unsupported_filters.0 == multi_player_availability`
- `lakers_record_without_luk_typo`
  - expected `team_record` / `no_result` / `ambiguous` or an approved
    unresolved-filter reason
  - hard assertion that sections are empty and no full team record appears

Targeted unit/integration tests:

- Parser tests for single-player presence phrases:
  - `Lakers record with Luka`
  - `Lakers record with Austin Reaves`
  - expected route `team_record` and resolved `with_player`
- Parser tests for mixed availability:
  - `Lakers record with Reaves without Luka`
  - expected `unsupported_filters=["multi_player_availability"]`
- Execution tests:
  - `execute_natural_query("Lakers record with Luka")` returns `team_record`
    with game log row count matching summary games.
  - `execute_natural_query("Lakers record with Reaves without Luka")` returns
    no-result and empty sections.
  - `execute_natural_query("Lakers record without Luk")` does not return
    `ok` full-team record.

### Parser / Routing Changes Needed

- Add a whole-game `with_player` availability slot distinct from on/off
  `presence_state`.
- Guard phrase forms:
  - `team record with PLAYER`
  - `team wins with PLAYER`
  - `team when PLAYER plays` if approved in the same wave
- Keep `with PLAYER on the floor` on the `player_on_off` path.
- Extend the multi-player availability boundary to catch mixed presence plus
  absence phrasing, including `with Reaves without Luka`.
- Preserve unresolved availability fragments instead of dropping them when
  `detect_without_player()` cannot resolve the name.

### Execution / Data Changes Needed

- Add a game-level `filter_with_player()` helper alongside
  `filter_without_player()`.
- Add `with_player` to `team_record.build_team_record_result()`.
- Build `game_log` for `with_player` team records, matching the existing
  without-player team-record detail behavior.
- Add caveat and metadata/applied-filter support for `With player`.
- Do not use `team_player_on_off_summary` for whole-game `with_player`.

### Frontend Copy / No-Result Changes Needed

- If `team_record` receives a `with_player` applied filter and caveat, the
  existing team-record renderer should be sufficient.
- If the typo path uses `result_reason=ambiguous`, verify `NoResultDisplay`
  copy does not imply the app ran a broad query.
- If a new `unresolved_without_player` unsupported-filter ID is chosen instead,
  add a specific note/copy path so users understand the player name was not
  resolved.

### Validation Commands

Recommended execution-wave validation:

```bash
make test-parser
make test-query
.venv/bin/python tools/raw_query_answer_qa.py --corpus qa/raw_query_answer_corpus.yaml --case lakers_record_with_luka --case lakers_record_with_reaves --case lakers_record_with_reaves_without_luka --case lakers_record_without_luk_typo --fail-on-expectation-failure
make test-preflight
git diff --check
```

If the implementation stays localized and does not touch high fan-in routing,
`make test-impacted` can be used for early iteration, but changes to
`natural_query.py` or parser core should use the parser/query slices and
preflight path above.

## 8. Preflight Validation

Run in this preflight:

```bash
.venv/bin/python - <<'PY'
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query
from nbatools.api_handlers import query_result_to_payload
PY

.venv/bin/nbatools-cli ask "Lakers record without Luka"
.venv/bin/nbatools-cli ask "Lakers record with Luka"
.venv/bin/nbatools-cli ask "Lakers record with Reaves without Luka"
.venv/bin/nbatools-cli ask "Lakers record without Luk"
.venv/bin/nbatools-cli ask "Luka stats this season"
.venv/bin/nbatools-cli ask "Who had the most rebounds in a game this year?"
```

To run after writing this document:

```bash
git diff --check
```

Markdown lint availability should be checked with:

```bash
command -v markdownlint
command -v markdownlint-cli2
command -v mdl
command -v mdformat
```
