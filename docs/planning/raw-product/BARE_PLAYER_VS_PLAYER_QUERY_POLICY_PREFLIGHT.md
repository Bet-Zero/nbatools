# Bare Player Vs Player Query Policy Preflight

Date: 2026-05-31

Mode: preflight completed; V1 implementation complete.

## 1. Scope

This document decided the product policy for bare player-vs-player natural
queries such as:

```text
LeBron vs KD
```

The original preflight did not change production code, parser/routing behavior,
frontend rendering, corpus expectations, release status, or Raw QA cases.
The follow-up V1 implementation changed only the narrow bare player-vs-player
behavior boundary, parser/query tests, Raw QA boundary cases, and current-state
docs named in this document.

The policy is intentionally narrow: "bare PLAYER vs PLAYER" means two resolved
player entities separated by `vs` / `versus` with no explicit comparison noun or
verb, no `stats` / `averages` / `game log` / `record` intent, no
`head-to-head` / `h2h` marker, and no playoff-history wording.

## 1.1 Implementation Status

V1 implementation is complete.

Bare player-vs-player queries now preserve the closest route
(`player_compare`) but return:

```text
result_status: no_result
result_reason: ambiguous_query
sections: {}
metadata.ambiguous_intent: bare_player_vs_player
```

Metadata also preserves recognized player context and provides
`clarification_options` for future UI work. See
`return_packages/raw-product/BARE_PLAYER_VS_PLAYER_AMBIGUOUS_BOUNDARY_V1_RETURN_PACKAGE.md`
for the temporary implementation evidence and validation receipt. Cleanup
trigger: replace this exact return-package path with durable generated-output
or reference-doc evidence when the bare player-vs-player clarification UI
workstream closes.

## 2. Read-First Sources

Read and applied:

- `docs/planning/raw-product/NATURAL_SEARCH_AND_DEEP_TOOLS_BOUNDARY.md`
- `docs/planning/raw-product/PUBLIC_QUERY_ACCEPTANCE_WAVE_2B_PROBE_RESULTS.md`
- `return_packages/raw-product/QUESTION_FORM_PLAYER_COMPARISON_ROUTING_FIX_RETURN_PACKAGE.md`
- `docs/reference/query_catalog.md`
- `docs/reference/query_guide.md`
- `qa/raw_query_answer_corpus.yaml`
- `qa/harness_slices/public_query_acceptance.yaml`

Important source constraints:

- Natural search can answer simple player comparisons when the intent is clear.
- The boundary doc explicitly classifies bare `LeBron vs KD` as ambiguous.
- The Wave 2B probe left bare `PLAYER vs PLAYER` policy open.
- The separate question-form comparison fix now supports
  `How do LeBron James and Kevin Durant compare this season?` as
  `player_compare` while preserving both players.
- The public corpus already distinguishes explicit player stat comparisons from
  player-opponent/head-to-head boundaries.

## 3. Pre-Implementation Behavior Probes

Probe path:

```text
nbatools.query_service.execute_natural_query(query)
nbatools.api_handlers.query_result_to_payload(result)
```

This is the same backend envelope path used by Raw QA, API responses, and the
React UI.

| Query | Pre-implementation route | Pre-implementation status | Pre-implementation interpretation |
| --- | --- | --- | --- |
| `LeBron vs KD` | `player_compare` | `ok` | Simple current-season player stat comparison; `head_to_head_used=false`; `summary: 2`, `comparison: 20`. |
| `LeBron James vs Kevin Durant` | `player_compare` | `ok` | Simple current-season player stat comparison; `head_to_head_used=false`; `summary: 2`, `comparison: 20`. |
| `Jokic vs Embiid` | `player_compare` | `ok` | Simple current-season player stat comparison; `head_to_head_used=false`; `summary: 2`, `comparison: 20`. |
| `Celtics vs Bucks` | `team_compare` | `ok` | Simple current-season team stat comparison; `head_to_head_used=false`; `summary: 2`, `comparison: 17`. |
| `Lakers vs Celtics` | `team_compare` | `ok` | Simple current-season team stat comparison; `head_to_head_used=false`; `summary: 2`, `comparison: 17`. |
| `LeBron stats vs KD` | `player_game_finder` | `ok` | Player-opponent game finder boundary; returns LeBron rows for games in the supported opponent-player sample. |
| `Lakers record vs Celtics` | `team_record` | `ok` | Lakers record with opponent filter `BOS`; `summary: 1`, `by_season: 1`. |

Supporting contrast probes:

| Query | Current route | Current status | Current interpretation |
| --- | --- | --- | --- |
| `Jokic head-to-head vs Embiid since 2021` | `player_compare` | `ok` | Explicit player head-to-head sample; `head_to_head_used=true`. |
| `Jokic game log vs Embiid` | `player_game_finder` | `no_result` | Game-log wording is not hijacked into stat comparison; current sample returns no match. |
| `Lakers vs Celtics head to head record` | `team_matchup_record` | `ok` | Explicit team matchup-record semantics; `head_to_head_used=true`. |
| `Lakers Celtics playoff matchup history` | `playoff_matchup_history` | `ok` | Explicit playoff matchup-history semantics; playoff sections returned. |

Before the V1 implementation, the parser used the same short `vs` token for several
distinct product intents. It can answer a plausible default, but it does not
know which of the valid meanings the user intended when the query is bare.

## 4. Intent Distinctions

Player stat comparison:

- Examples: `Compare LeBron James and Kevin Durant`,
  `LeBron James vs Kevin Durant comparison`,
  `How do LeBron James and Kevin Durant compare this season?`,
  `Jokic vs Embiid recent form`.
- Expected route family: `player_compare`.
- Product meaning: compare player stat samples side by side.

Team stat comparison:

- Examples: `Celtics vs Bucks comparison this season`,
  `Celtics vs Bucks from 2021-22 to 2023-24`.
- Expected route family: `team_compare`.
- Product meaning: compare team stat samples side by side.

Player head-to-head / games against:

- Examples: `Jokic head-to-head vs Embiid since 2021`,
  `LeBron stats vs Kevin Durant`, `Jokic game log vs Embiid`.
- Expected route families: player comparison with `head_to_head_used=true`, or
  a player finder/summary route with an opponent-player interpretation when the
  wording asks for stats, averages, or game rows.
- Product meaning: restrict the sample to games involving the opponent player
  context, not a broad independent season comparison.

Team matchup record:

- Examples: `Lakers record vs Celtics`,
  `Lakers vs Celtics head to head record`.
- Expected route families: `team_record` with an opponent filter, or
  `team_matchup_record` when the phrase asks for a two-sided matchup record.
- Product meaning: team games against the other team.

Playoff matchup history:

- Examples: `Lakers Celtics playoff matchup history`,
  `Lakers playoff series record vs Celtics`.
- Expected route family: `playoff_matchup_history`.
- Product meaning: postseason series/history, not current-season comparison.

## 5. User Expectation Evaluation

Sports users often use `vs` to mean "compare these two players." The
pre-implementation silent default was therefore understandable, and it returned
a coherent answer for many search-bar style queries.

Sports users also use `vs` to mean "games against," "head-to-head," "team
matchup," or "playoff matchup." The query `LeBron vs KD` has no words that
choose among those meanings. Accepting the current stat-comparison route as a
public contract would lock in one interpretation while the product is already
planning deeper comparison and head-to-head tools.

The most important product risk is not that the current answer is nonsensical;
it is that the answer is silently specific where the query is genuinely
underspecified.

## 6. Policy Decision

V1 policy: option C is implemented, and the product does not public-accept the
old silent comparison default.

```text
Bare PLAYER vs PLAYER should return a clean ambiguous/unsupported response until
the product has a clarification UI and typed clarification response contract.
```

This is the safest V1 public policy because it avoids blessing a silent default
that can mean multiple sports intents. It also preserves room for the future
Player Comparison Tool and Head-to-Head Tool without turning today's heuristic
into a long-term public promise.

Implementation note: V1 preserves `player_compare` as the closest route, but
returns `no_result` / `ambiguous_query` with empty sections instead of executing
the comparison table.

## 7. Future Ideal Policy

Future ideal behavior: choose option B once clarification UI and response
contracts exist.

For bare `PLAYER vs PLAYER`, natural search should return an ambiguity response
with intent options such as:

- compare season stats
- show head-to-head games
- show one player stats in games against the other player
- show playoff matchup history if applicable and supported

The API should expose a typed ambiguity/clarification payload rather than a
free-text error. The CLI can render the options as numbered suggestions. The
React UI can render intent chips that resubmit clarified queries.

Option A, defaulting bare `PLAYER vs PLAYER` to simple player comparison, should
remain available only as an explicit future product choice after ambiguity
handling is rejected or deferred with a durable rationale.

## 8. Corpus Implications

Do not add a public-acceptance expected-ok case for bare `LeBron vs KD`,
`LeBron James vs Kevin Durant`, or `Jokic vs Embiid` as an executing
comparison table.

Keep accepted comparison coverage on disambiguated comparison phrasing:

- `LeBron James vs Kevin Durant comparison`
- `Compare LeBron James and Kevin Durant`
- `How do LeBron James and Kevin Durant compare this season?`
- `Jokic vs Embiid recent form`

Keep boundary coverage for opponent/head-to-head semantics:

- `LeBron stats vs Kevin Durant`
- `Jokic game log vs Embiid`
- explicit `head-to-head` / `h2h` forms

The V1 implementation adds Raw QA boundary cases for bare `PLAYER vs PLAYER`
that expect a clean ambiguous result:

```text
expected_status: no_result
expected_reason: ambiguous_query
expected_shape: no_result
expected_route: player_compare
```

If option B lands later, update Raw QA to assert the typed ambiguity payload and
the presence of supported intent options. Do not assert a comparison table for
the bare query.

## 9. Documentation Implications

Docs should not advertise bare `LeBron vs KD` as a supported public query.

Docs should advertise disambiguated comparison wording instead:

- `Compare LeBron and KD this season`
- `LeBron James vs Kevin Durant comparison`
- `How do LeBron James and Kevin Durant compare this season?`
- `Jokic vs Embiid recent form`

Docs can mention bare `PLAYER vs PLAYER` only as an ambiguity/clarification
candidate. `docs/reference/query_catalog.md` and `docs/reference/query_guide.md`
now document the V1 `no_result` / `ambiguous_query` boundary and use
disambiguated comparison wording for supported examples.

## 10. Future Clarification Stop Conditions

Stop before implementing typed clarification UI if any of these are unresolved:

- no approved typed ambiguity/clarification response shape for API consumers
- no agreed CLI rendering for ambiguity options
- no agreed React UI rendering for clarification options
- no route/reason contract for replacing the V1 `ambiguous_query` response
- corpus expectations would encode an executing comparison table for bare
  `PLAYER vs PLAYER`
- docs would advertise bare `LeBron vs KD` as supported comparison shorthand
- implementation would weaken explicit routes such as
  `LeBron stats vs Kevin Durant`, `Lakers record vs Celtics`,
  `Lakers vs Celtics head to head record`, or
  `Lakers Celtics playoff matchup history`

Minimum acceptance for a later clarification wave:

- parser/routing tests for bare player-vs-player ambiguity
- regression tests proving explicit comparison, player-opponent, team matchup,
  and playoff-history wording still route correctly
- Raw QA boundary coverage for the chosen public contract
- updated query catalog and guide wording after behavior is verified
- no frontend business logic; UI renders the API-provided ambiguity contract

## 11. Recommendation Summary

V1 policy:

- Bare `PLAYER vs PLAYER` is ambiguous.
- Do not public-accept or advertise it as `player_compare`.
- Preferred implementation before clarification UI: clean ambiguous/unsupported
  response.

Future ideal:

- Return typed clarification options.
- Let the user choose simple comparison, head-to-head, opponent-player stats, or
  matchup/history where supported.

Current behavior:

- `player_compare / no_result / ambiguous_query` for bare player-vs-player.
- Disambiguated comparison, player-opponent finder, team comparison, team
  matchup record, and playoff matchup history behavior are preserved.

## 12. Validation

Preflight docs validation was superseded by the V1 implementation wave. See
the temporary return-package handoff named in Section 1.1 for implementation
validation results.

Original docs-only validation:

| Check | Result |
| --- | --- |
| `git diff --check` | Passed for tracked diff. |
| `git diff --check --no-index /dev/null docs/planning/raw-product/BARE_PLAYER_VS_PLAYER_QUERY_POLICY_PREFLIGHT.md` | No whitespace warnings; exit code `1` is expected for `/dev/null` comparisons with file content. |
| `git diff --check --no-index /dev/null return_packages/raw-product/BARE_PLAYER_VS_PLAYER_QUERY_POLICY_PREFLIGHT_RETURN_PACKAGE.md` | No whitespace warnings; exit code `1` is expected for `/dev/null` comparisons with file content. |
| Markdown lint availability | Not run; no `markdownlint`, `markdownlint-cli2`, `mdl`, or `mdformat` command was found on PATH, and no repo-local markdown lint target was found in `Makefile`, `pyproject.toml`, or `frontend/package.json`. |
