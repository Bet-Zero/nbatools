# Public Query Acceptance Wave 2B Probe Results

Date: 2026-05-31

Status: probe documentation plus follow-up fix note. The Wave 2B probe pass
itself changed no behavior. A later narrow routing fix corrected the
question-form player comparison bug documented here. Bare `PLAYER vs PLAYER`
now has a V1 ambiguous/no-result boundary. Public-acceptance status remains
open.

## Scope

Wave 2B probed product-decision and semantics-risk queries named by
`PUBLIC_QUERY_ACCEPTANCE_PRODUCT_REVIEW_TRIAGE.md`.

Probe execution used the backend payload path:

```text
nbatools.query_service.execute_natural_query(query)
nbatools.api_handlers.query_result_to_payload(result)
```

This is the same response envelope consumed by the API and React UI. The probe
run did not add expected-ok cases and did not encode current bad behavior.

## Read-First Context

Read and applied:

- `outputs/raw_query_answer_qa/20260531T073042Z_wave2a_taxonomy_safe_retags/product_review.md`
- `working/public-query-acceptance-review/PUBLIC_QUERY_ACCEPTANCE_PRODUCT_REVIEW_TRIAGE.md`
- `docs/reference/natural_search_and_deep_tools_boundary.md`
- `qa/raw_query_answer_corpus.yaml`
- `qa/harness_slices/public_query_acceptance.yaml`
- `docs/reference/query_catalog.md`
- `docs/reference/query_guide.md`

Important context from those files:

- Wave 2A completed taxonomy and metadata work only; all public families remain
  not accepted and human review remains pending.
- The natural-search boundary says clear simple comparisons are in scope, but
  bare `PLAYER vs PLAYER` queries are inherently ambiguous.
- Threshold-less count phrasing such as `how many players played this season`
  is documented as unsupported.
- Several current unsupported rows are allowed to remain `error` / `unrouted`
  during metadata rollout, but future cleanup should consider route-preserving
  `no_result` / `filter_not_supported` semantics for recognizable unsupported
  concepts.

## Classification Summary

| Query | Route | Status | Reason | Sections | Preserves intended scope | Broad fallback | Classification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `LeBron vs KD` | `player_compare` | `ok` |  | `summary: 2`, `comparison: 20` | Preserves one plausible comparison scope, but the query is ambiguous. | No. | Product decision required. |
| `How do LeBron James and Kevin Durant compare this season?` | `player_game_summary` | `ok` |  | `summary: 1`, `by_season: 1`, `game_log: 60` | No. Kevin Durant is dropped. | Not league-wide, but it falls to the wrong single-player scope. | Behavior bug; fixed in follow-up routing wave. |
| `Who are the MVP candidates?` |  | `error` | `unrouted` | none | Yes, because it declines an unsupported awards/narrative request. | No. | Semantic cleanup candidate; acceptable unsupported behavior for now. |
| `who has cooled off lately` |  | `error` | `unrouted` | none | Yes, because trend/drop-off semantics are not defined. | No. | Semantic cleanup candidate; acceptable unsupported behavior for now. |
| `how many players played this season` |  | `error` | `unrouted` | none | Yes, because threshold-less player population counts are not supported. | No. | Acceptable unsupported behavior; semantic cleanup candidate. |
| `most rebunds in a game this season` |  | `error` | `unrouted` | none | Yes, because it does not silently answer a different stat. | No. | Semantic cleanup candidate. |
| `Lakeers playoff history` |  | `error` | `unrouted` | none | Yes, because it does not silently correct the team typo or return broad playoff history. | No. | Semantic cleanup candidate. |

At initial probe time, no required probe was a safe expected-ok corpus addition.
After the follow-up routing fix, the question-form comparison query is safe to
encode. Bare `vs` remains excluded until its product policy is decided.

Follow-up fix notes:

- `How do LeBron James and Kevin Durant compare this season?` now routes to
  `player_compare` with status `ok`.
- The fixed payload preserves both LeBron James and Kevin Durant in
  `metadata.players_context`, `summary`, and `comparison`.
- Bare `LeBron vs KD` was later changed in a separate narrow V1 boundary wave
  to `player_compare / no_result / ambiguous_query`.
- The fixed question-form query was added to the Raw QA corpus as
  `question_form_lebron_durant_comparison_wave2b`.

## Probe Details

### 1. `LeBron vs KD`

| Field | Value |
| --- | --- |
| Route | `player_compare` |
| Status | `ok` |
| Reason |  |
| Result shape | comparison payload |
| Sections | `summary: 2`, `comparison: 20` |
| Applied filters | Default `season: 2025-26`; `season_type: Regular Season`; `scope_kind: single_season` |
| Unsupported filters | none |
| Current through | `2026-04-12` |

Answer summary / top rows:

- `summary` includes LeBron James and Kevin Durant.
- LeBron James: `60` games, `20.933` PPG, `6.067` RPG, `7.2` APG.
- Kevin Durant: `78` games, `25.974` PPG, `5.462` RPG, `4.769` APG.
- `comparison` starts with metrics `games`, `wins`, and `losses`.

Scope review:

- The result preserves a valid simple player-comparison interpretation.
- It does not broad-fall back to a league-wide table or unrelated route.
- It still answers one of several plausible meanings for a bare `vs` query:
  player stat comparison, player head-to-head games, team head-to-head games, or
  playoff matchup history.

Classification:

- Current behavior is not safe to encode as accepted until product policy is
  explicit.
- Primary classification: product decision required.

Bare `vs` recommendation:

- Recommend option 1: clarification / intent options.
- Rationale: the boundary document already identifies bare `LeBron vs KD` as
  ambiguous, and current behavior silently chooses one interpretation. A
  clarification response can offer simple comparison, player head-to-head games,
  or team/playoff matchup intent without implying that one is always intended.
- Do not add an expected-ok corpus row for bare `LeBron vs KD` before this
  product decision is accepted. If the product later chooses option 2, the
  current result is a plausible default simple comparison candidate. If
  clarification cannot be implemented yet, a clean unsupported/ambiguous result
  is safer than public-accepting the silent default.

### 2. `How do LeBron James and Kevin Durant compare this season?`

| Field | Value |
| --- | --- |
| Route | `player_game_summary` |
| Status | `ok` |
| Reason |  |
| Result shape | single-player summary payload |
| Sections | `summary: 1`, `by_season: 1`, `game_log: 60` |
| Applied filters | Default `season: 2025-26`; `season_type: Regular Season`; `player: LeBron James`; note `default: <player> + <timeframe> -> summary` |
| Unsupported filters | none |
| Current through | `2026-04-12` |

Answer summary / top rows:

- The payload summarizes only LeBron James.
- LeBron James: `60` games, `20.933` PPG, `6.067` RPG, `7.2` APG.
- `game_log` includes `60` LeBron rows.
- Kevin Durant is absent from metadata and sections.

Scope review:

- Intended scope is explicit player comparison between LeBron James and Kevin
  Durant this season.
- The result does not preserve intended scope because it drops Kevin Durant.
- It is not a league-wide broad fallback, but it is a wrong-scope fallback to a
  single-player summary.

Classification:

- Behavior bug, now fixed.
- The pre-fix LeBron-only result must not be encoded as expected.
- The fixed query is now a Raw QA corpus case in the `comparisons` family with
  expected route `player_compare`, status `ok`, and sections `summary` plus
  `comparison`.

Supporting comparison probes:

| Query | Route | Status | Sections | Note |
| --- | --- | --- | --- | --- |
| `Compare LeBron James and Kevin Durant this season` | `player_compare` | `ok` | `summary: 2`, `comparison: 20` | Explicit compare verb works. |
| `LeBron James vs Kevin Durant comparison` | `player_compare` | `ok` | `summary: 2`, `comparison: 20` | Existing documented style works. |
| `LeBron James vs Kevin Durant this season` | `player_compare` | `no_result` | none | Returns `filter_not_supported` with `unsupported_filters=["unresolved_player"]`; separate semantics-risk candidate. |
| `LeBron James vs Kevin Durant last 10 games` | `player_compare` | `ok` | `summary: 2`, `comparison: 20` | Last-N comparison works. |

The bug is therefore specific to the question-form `How do A and B compare...`
parse, not to all LeBron/Durant comparison execution.

### 3. `Who are the MVP candidates?`

| Field | Value |
| --- | --- |
| Route |  |
| Status | `error` |
| Reason | `unrouted` |
| Result shape | error payload |
| Sections | none |
| Applied filters | none |
| Unsupported filters | none |

Answer summary / top rows:

- No answer text.
- No result sections.

Scope review:

- The request is awards/narrative/forecasting oriented.
- Current behavior does not invent a leaderboard or silently map MVP candidates
  to points-per-game leaders.
- It does not broad-fall back.

Classification:

- Semantic cleanup candidate; acceptable unsupported behavior for now.
- Existing corpus already contains this query as `mvp_candidates_subjective`.
- Future cleanup can consider a route-preserving unsupported result, but this is
  not a behavior fix prerequisite for Wave 2B.

### 4. `who has cooled off lately`

| Field | Value |
| --- | --- |
| Route |  |
| Status | `error` |
| Reason | `unrouted` |
| Result shape | error payload |
| Sections | none |
| Applied filters | `Last N games=10`; default `season: 2025-26`; `season_type: Regular Season` |
| Unsupported filters | none |
| Current through | `2026-04-12` |

Answer summary / top rows:

- No answer text.
- No result sections.

Scope review:

- The query includes a recognized recency signal, but "cooled off" does not have
  a defined metric-backed interpretation.
- Current behavior does not return a broad "recent form" leaderboard or an
  unrelated streak table.
- It does not broad-fall back.

Classification:

- Semantic cleanup candidate; acceptable unsupported behavior for now.
- Existing corpus already contains this query as `cooled_off_lately_wave5`.
- Future cleanup should decide whether this remains unsupported with a cleaner
  unsupported reason, or whether a measurable drop-off metric is product-owned.

### 5. `how many players played this season`

| Field | Value |
| --- | --- |
| Route |  |
| Status | `error` |
| Reason | `unrouted` |
| Result shape | error payload |
| Sections | none |
| Applied filters | none |
| Unsupported filters | none |

Answer summary / top rows:

- No answer text.
- No result sections.

Scope review:

- The query asks for a population count without a stat threshold.
- The query catalog explicitly states that count support requires a stat plus
  threshold and that this phrasing is not supported.
- Current behavior does not return a broad leaderboard or unrelated count.
- It does not broad-fall back.

Classification:

- Acceptable unsupported behavior; semantic cleanup candidate.
- Existing corpus already contains this query as
  `pqa_count_unsupported_players_played`.
- Keep current expectation during Wave 2B. A later cleanup may return
  `no_result` / `filter_not_supported` with a clearer unsupported-count reason.

### 6. `most rebunds in a game this season`

| Field | Value |
| --- | --- |
| Route |  |
| Status | `error` |
| Reason | `unrouted` |
| Result shape | error payload |
| Sections | none |
| Applied filters | none |
| Unsupported filters | none |

Answer summary / top rows:

- No answer text.
- No result sections.

Scope review:

- The intended feature is likely top single-game rebounds, but the stat token is
  misspelled.
- Current behavior correctly avoids answering "most points in a game" or another
  broad top-game default.
- It does not broad-fall back.

Classification:

- Semantic cleanup candidate.
- Existing corpus already contains this query as `pqa_top_games_stat_typo_rebunds`.
- This matches the triage note that the row needs investigation before any
  status change. A later cleanup could preserve the likely `top_player_games`
  intent and return `no_result` / `filter_not_supported` with an unresolved-stat
  unsupported filter, but current no-broad-fallback behavior is safer than a bad
  answered result.

### 7. `Lakeers playoff history`

| Field | Value |
| --- | --- |
| Route |  |
| Status | `error` |
| Reason | `unrouted` |
| Result shape | error payload |
| Sections | none |
| Applied filters | `season_type: Playoffs` |
| Unsupported filters | none |

Answer summary / top rows:

- No answer text.
- No result sections.

Scope review:

- The intended feature is likely single-team playoff history, but the team token
  is misspelled.
- Current behavior correctly avoids silently correcting `Lakeers` to Lakers or
  returning a broad playoff-history result.
- It does not broad-fall back.

Classification:

- Semantic cleanup candidate.
- Existing corpus already contains this query as
  `pqa_playoff_typo_lakeers_history`.
- This matches the triage note that the row needs investigation before any
  status change. A future cleanup could preserve the likely `playoff_history`
  intent and return `no_result` / `filter_not_supported` with an unresolved-team
  unsupported filter.

## Product Decision: Bare `LeBron vs KD`

Decision implemented for V1: clean ambiguous/no-result boundary until typed
clarification UI exists.

Future ideal public behavior:

```text
Ambiguous comparison. Did you mean:
- compare LeBron James and Kevin Durant stats this season
- show LeBron games against Kevin Durant
- show Kevin Durant games against LeBron
- show team or playoff head-to-head history
```

Implementation note:

- V1 preserves `player_compare` as the closest route and returns
  `no_result` / `ambiguous_query` with empty sections.
- Metadata preserves the recognized players and a `bare_player_vs_player`
  ambiguity marker for future typed clarification UI.
- The old `player_compare / ok` table is not a public-accepted expectation for
  bare player-vs-player phrasing.

## Behavior Bugs Versus Product Decisions

Behavior bugs:

- `How do LeBron James and Kevin Durant compare this season?` dropped Kevin
  Durant and returned a LeBron-only `player_game_summary`; fixed in the
  question-form player comparison routing wave.

Product decisions:

- Bare `LeBron vs KD` now has an explicit V1 product policy:
  `player_compare / no_result / ambiguous_query`, with future typed
  clarification options deferred.

Acceptable unsupported behavior:

- `how many players played this season` is documented unsupported because count
  queries require a stat plus threshold.

Semantic cleanup candidates:

- `Who are the MVP candidates?`
- `who has cooled off lately`
- `how many players played this season`
- `most rebunds in a game this season`
- `Lakeers playoff history`

Safe corpus additions:

- `How do LeBron James and Kevin Durant compare this season?` after the
  follow-up fix, as `question_form_lebron_durant_comparison_wave2b`.
- Bare player-vs-player boundary rows after the V1 boundary wave:
  `bare_lebron_kd_ambiguous_boundary_v1`,
  `bare_lebron_durant_ambiguous_boundary_v1`, and
  `bare_jokic_embiid_ambiguous_boundary_v1`.

## Concrete Next Action

1. Keep the V1 bare `PLAYER vs PLAYER` ambiguity boundary until typed
   clarification UI and API response contracts are approved.
2. Open a separate semantic-cleanup wave for recognizable unsupported concepts
   that currently return `error` / `unrouted`, prioritizing route-preserving
   `no_result` / `filter_not_supported` where the main intent is clear.
3. Do not mark any family public accepted until the variant matrix is resolved,
   representative outputs are human-reviewed, and the behavior/product decisions
   above are closed.
