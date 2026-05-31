# Public Query Acceptance Product Review Triage

Date: 2026-05-31

Status: Wave 2A comparison-taxonomy migration and safe metadata retags
complete; Wave 2B probes are documented and the question-form player
comparison routing bug is fixed. Bare `LeBron vs KD` now has a V1
ambiguous/no-result boundary. Human rendered-output review remains pending.

## 1. Scope

This is a documentation-only triage of:

```text
outputs/raw_query_answer_qa/20260531T064312Z_wave1_public_acceptance/product_review.md
```

This pass does not change production code, parser/routing behavior, query
result behavior, frontend rendering, release status, corpus expectations, or
public-acceptance claims.

The generated artifact is doing the intended job: it separates a green machine
run from family coverage, human review, and public acceptance.

## 2. Artifact Summary

| Metric | Result |
| --- | --- |
| Cases run | `67` |
| Registered families | `17` |
| Public-surface families | `15` |
| Guardrail-only families | `2` |
| Families with complete variant coverage | `1`: `team_record_availability` |
| Families with missing variants | `16` |
| Machine regression | `pass` |
| Human review declaration | `human_review_pending` |
| Public-accepted families | `0` |
| Generated suspicious rows | `0` |
| Generated product-decision rows | `1` |

The one generated product decision is real: `comparisons` and
`player_comparisons` overlap and should not remain separate public families.

### 2.1 Review Observations

The generated suspicious-row list is empty. This triage found no machine-proof
failure in the selected slice.

The following rows are not current expectation failures, but they deserve
explicit Wave 2 handling:

| Area | Observation | Disposition |
| --- | --- | --- |
| Comparison taxonomy | `pqa_comparison_subjective_better_jokic_embiid` is owned by `comparisons`, while `pqa_comparison_typo_kevn_durant` is owned by `player_comparisons`. | Collapse to one public family before broad retagging. |
| Unrouted public boundaries | `16` no-broad-fallback rows pass as route `None`, status `error`, reason `unrouted`. | Keep current expectations during metadata rollout; classify a later semantics-cleanup wave in section 6. |
| Representative cards | Backend answer text is often `_not backend-provided_`. | Not a backend defect. The public frontend hero copy still needs rendered review. |
| Summary cards | Player and team summaries include `64`-row `game_log` sections. | Scope looks plausible, but rendered density needs frontend review. |

## 3. Comparison Taxonomy Decision

Adopt one public family:

```text
comparisons
```

Remove the separate public family:

```text
player_comparisons
```

Typo and partial-name behavior is a comparison boundary, not a second feature
family.

### 3.1 Comparison Concepts

| Concept | Purpose | Initial evidence |
| --- | --- | --- |
| `player_stat_comparison` | Side-by-side player comparison over a shared sample. | `lebron_durant_comparison_wave4`, `jokic_embiid_recent_comparison`, `compare_lebron_durant_wave5` |
| `team_stat_comparison` | Side-by-side team comparison over a shared sample. | `celtics_bucks_comparison_this_season_wave5` |
| `player_head_to_head_boundary` | Distinguish comparison from player-as-opponent finder wording. | `lebron_stats_vs_durant_wave5` |
| `team_head_to_head_boundary` | Keep team comparison and matchup-record wording intentional. | `lakers_celtics_h2h_record_wave4`, `heat_knicks_h2h_since_2020_wave4` |
| `subjective_comparison_boundary` | Decline winner/value judgments without inventing an answer. | `pqa_comparison_subjective_better_jokic_embiid` |
| `comparison_entity_resolution` | Reject unresolved comparison entities without silently choosing aliases. | `pqa_comparison_typo_kevn_durant` |
| `ambiguous_vs_clarification_candidate` | Track bare `PLAYER vs PLAYER` phrasing that needs clarification rather than a default answer. | `bare_lebron_kd_ambiguous_boundary_v1`, `bare_lebron_durant_ambiguous_boundary_v1`, `bare_jokic_embiid_ambiguous_boundary_v1` |

### 3.2 Exact Registry Migration

1. Delete the `player_comparisons` registry entry.
2. Remove `player_comparisons` from `comparisons.sibling_families`.
3. Change `player_summaries_recent_form.sibling_families` from
   `player_comparisons` to `comparisons`.
4. Retag `pqa_comparison_typo_kevn_durant` from `player_comparisons` to
   `comparisons` with concept `comparison_entity_resolution`.
5. Add concept `subjective_comparison_boundary` to
   `pqa_comparison_subjective_better_jokic_embiid`.
6. Retag the existing comparison cases in the table below. Do not add duplicate
   corpus rows.

| Variant | Existing case to retag | Concept |
| --- | --- | --- |
| `canonical` | `lebron_durant_comparison_wave4` | `player_stat_comparison` |
| `short` | `jokic_embiid_recent_comparison` | `player_stat_comparison` |
| `sentence` | `compare_lebron_durant_wave5` | `player_stat_comparison` |
| `synonym` | `celtics_bucks_comparison_this_season_wave5` | `team_stat_comparison` |
| `inverse_sibling` | `lebron_stats_vs_durant_wave5` | `player_head_to_head_boundary` |
| `nearby_unsupported` | `pqa_comparison_subjective_better_jokic_embiid` | `subjective_comparison_boundary` |
| `typo_partial` | `pqa_comparison_typo_kevn_durant` | `comparison_entity_resolution` |

`lebron_durant_comparison_wave4` currently fills
`player_summaries_recent_form.inverse_sibling`. Replace that coverage with the
existing `tatum_brown_last10_comparison_wave4` case when moving the canonical
comparison row.

### 3.3 Bare `vs` Product Decision

The natural-search boundary document says a bare query such as `LeBron vs KD`
is inherently ambiguous. V1 implements the clean ambiguous/no-result choice:

```text
route: player_compare
result_status: no_result
result_reason: ambiguous_query
metadata.ambiguous_intent: bare_player_vs_player
```

Future clarification UI can replace this with typed intent options. The other
product options considered during preflight were:

- return clarification or intent options
- choose and document a default simple comparison
- return a clean unsupported/ambiguous result until clarification exists

Do not encode the old silent comparison-table behavior as expected.

## 4. Missing Variant Triage

`add safe expectation now` below means reuse and retag an existing passing
corpus row. It does not mean weaken or invent an expectation.

### 4.1 Public Feature Families

| Family | Artifact missing variants | Add safe expectation now | Probe first | Behavior fix needed | Product decision needed | Not applicable |
| --- | --- | --- | --- | --- | --- | --- |
| `player_stats_this_season` | `inverse_sibling` | Retag `luka_40_point_count` as a count/finder sibling. | None. | None proven. | None. | None. |
| `team_records` | `synonym` | Retag `lakers_road_record_last_season`. | None. | None proven. | None. | None. |
| `team_record_availability` | None | No matrix change. | None. | None proven. | None. | None. |
| `player_summaries_recent_form` | `short`, `sentence`, `synonym`, `nearby_unsupported` | Retag `luka_last_10_summary_wave5`, `tatum_good_teams`, `kd_ts_top_defenses_missing_filters`, and `best_player_lately_ambiguous`. Replace the moved comparison sibling with `tatum_brown_last10_comparison_wave4`. | None. | None proven. | None. | None. |
| `leaderboards` | `short`, `sentence`, `synonym`, `inverse_sibling` | Retag `leaders_in_steals_wave5`, `centers_rebound_leaders_wave4`, `true_shooting_leaders_phrase_wave5`, and `most_assists_single_game`. | None. | None proven. | None. | None. |
| `top_single_game_performances` | `short`, `inverse_sibling`, `nearby_unsupported` | Retag `most_rebounds_single_game`, `rebound_leaders_this_season`, and `biggest_team_three_point_games_boundary`. | None. | None proven. | None. | None. |
| `count_queries` | `sentence`, `synonym`, `inverse_sibling` | Retag `celtics_120_15_threes_count_missing_filter`, `players_10_assist_count`, and `jokic_30_10_10_finder`. | None. | None proven. | None. | None. |
| `game_finders` | `short`, `inverse_sibling`, `nearby_unsupported` | Retag `curry_5_threes_finder`, `anthony_edwards_last_10_summary_no_match`, and `celtics_bench_scoring_boundary_wave4`. | None. | None proven. | None. | None. |
| `splits` | `short`, `sentence`, `synonym`, `inverse_sibling` | Retag `celtics_wins_losses_split`, `anthony_edwards_wins_losses_split_no_match`, `curry_home_away_last_20_split_wave4`, and `knicks_road_record`. | None. | None proven. | None. | None. |
| `streaks` | `short`, `synonym`, `inverse_sibling` | Retag `lakers_win_streak`, `thunder_110_point_streak`, and `curry_5_threes_count`. | None. | None proven. | None. | None. |
| `rolling_stretches` | `short`, `synonym`, `nearby_unsupported` | Retag `booker_4_game_scoring_stretch`, `efficient_10_game_stretch`, and `team_net_rating_stretch_unsupported`. | None. | None proven. | None. | None. |
| `comparisons` | `canonical`, `short`, `sentence`, `synonym`, `inverse_sibling`, `typo_partial` | Apply the exact retags in section 3.2 and include the V1 bare-`vs` ambiguity boundary cases. | None. | None proven after the V1 boundary. | Future typed clarification UI remains deferred. | None. |
| `player_comparisons` | `canonical`, `short`, `sentence`, `synonym`, `inverse_sibling`, `nearby_unsupported` | None. | None. | None. | Collapse the family into `comparisons`. | Remove the overlapping family after migrating its typo guard into `comparisons`. |
| `playoff_history` | `short`, `sentence`, `synonym` | Retag `lakers_finals_appearances`, `lakers_celtics_playoff_matchup_history_wave5`, and `heat_knicks_playoff_series_record_wave4`. | None. | None proven. | None. | None. |
| `date_window_filters` | `short`, `sentence`, `synonym` | Retag `luka_last_5_summary`, `specific_date_jan_1`, and `jokic_since_all_star_break`. | None. | None proven. | None. | None. |

### 4.2 Guardrail Families

| Family | Artifact missing variants | Add safe expectation now | Probe first | Behavior fix needed | Product decision needed | Not applicable |
| --- | --- | --- | --- | --- | --- | --- |
| `unsupported_subjective_narrative` | `sentence`, `inverse_sibling` | Retag `cooled_off_last_10` and `tatum_clutch_stats`. | Probe the public rendered copy for unrouted subjective rows before claiming UX closure. | Future reason/status cleanup is classified in section 6. | Decide whether semantic normalization is needed after rendered review. | None. |
| `typo_partial_entity_behavior` | `canonical`, `sentence`, `synonym`, `inverse_sibling`, `nearby_unsupported` | No additional generic retags. Keep the existing `short` and `typo_partial` cross-family checks. | Probe only when adding a new typo domain. | None proven. | None. | Mark the five missing variants `not_applicable`: domain-specific typo guards belong to their owning feature families. |

### 4.3 Family-Specific Variant Rule

The seven-variant grid is a review checklist, not a requirement to force every
label onto every family.

Use `not_applicable_variants` only with a concrete reason. For Wave 2:

- keep all seven required variants for public feature families
- keep all seven for `unsupported_subjective_narrative`
- mark `canonical`, `sentence`, `synonym`, `inverse_sibling`, and
  `nearby_unsupported` not applicable for `typo_partial_entity_behavior`
- remove `player_comparisons` after the taxonomy migration

Do not use `not_applicable` to hide a public feature gap.

## 5. Representative Output Review

The artifact exposes backend-structured summaries, not the final public hero
copy. `_not backend-provided_` is expected for these cards.

| Case | Classification | Review notes |
| --- | --- | --- |
| `points_per_game_leader` | Looks correct; needs frontend rendered review. | Route, status, shape, and top row are plausible: Luka Doncic leads the shown `2025-26` PPG table. Confirm the public leaderboard headline and supporting columns. |
| `lakers_record_with_luka_public_sweep` | Looks correct; possible rendering-density issue; needs frontend rendered review. | Scope is preserved as Lakers team record with Luka Doncic. The `64`-row game log may be visually heavy even though the data shape is valid. |
| `lakers_record_with_reaves_without_luka_public_sweep` | Looks correct; needs frontend rendered review. | Compound availability fails cleanly as `team_record` / `no_result` / `filter_not_supported`. Confirm the UI explains the unsupported combination without generic error copy. |
| `pqa_player_stats_sentence_luka_played` | Looks correct; possible rendering-density issue; needs frontend rendered review. | Scope is Luka Doncic player summary for `2025-26`. The `64`-row game log may be correct but visually heavy. Confirm the frontend hero copy rather than relying on the harness summary. |

No representative card should be marked human-reviewed until the public
frontend rendering is actually inspected.

## 6. Error Versus No-Result Review

The current frontend checks `reason === "unrouted"` before generic error
handling. An API result with status `error` and reason `unrouted` therefore
renders as `Unsupported Query`, not as a transport or server failure. This is a
code-path inference and still needs rendered verification.

Keep current expectations unchanged during Wave 2. Open a later cleanup wave
for semantic normalization.

### 6.1 Acceptable Internal Error If Public UI Renders Clean Unsupported

These unresolved entity fragments can remain `error` / `unrouted` in V1
because the parser cannot confidently bind the requested subject:

- `pqa_player_stats_typo_jokc`
- `pqa_player_recent_typo_tatm`
- `pqa_count_typo_jokc_triple_doubles`
- `pqa_finder_typo_curr_5_threes`
- `pqa_split_typo_jokc_home_away`
- `pqa_streak_typo_jok_longest`
- `pqa_typo_short_jokc_stats`

### 6.2 Future Conversion To `no_result` / `filter_not_supported`

These queries express a recognizable unsupported concept. A later cleanup wave
should consider route-preserving `no_result` semantics:

- `best_defender_subjective`
- `mvp_candidates_subjective`
- `best_duo_unsupported`
- `cooled_off_lately_wave5`
- `pqa_count_unsupported_players_played`
- `pqa_subjective_short_mvp_candidates`

This is cleanup, not a reason to rewrite expectations during metadata rollout.

### 6.3 Needs Investigation

These rows are inconsistent with similar route-preserving guards and should be
probed before any status change:

- `pqa_top_games_stat_typo_rebunds`
- `pqa_playoff_typo_lakeers_history`
- `pqa_subjective_typo_defnder`

The decision rule is confidence-based: preserve a route only when the engine
can confidently identify the intended feature and reject the unresolved
qualifier without widening scope.

## 7. Wave 2 Execution Plan

### Wave 2A: Comparison Taxonomy And Safe Metadata Retags

Goal: resolve taxonomy first and fill visible matrix gaps using existing
passing corpus rows only.

Implement:

1. Apply the comparison registry migration in section 3.2.
2. Apply the safe existing-case retags in section 4.
3. Add concept, review role, sibling, intent-model, and qualifier-model
   metadata where it improves review clarity.
4. Add at least one representative `review_required` card for each public
   feature family before any acceptance claim.
5. Regenerate `product_review.md`.

Do not:

- change existing route/status/reason expectations
- add a new expected-ok query without probing it first
- change production behavior
- mark any family public accepted

#### Wave 2A Completion Notes

Wave 2A completed on 2026-05-31 as behavior-neutral metadata and corpus
organization work.

Completed:

- collapsed `player_comparisons` into the single public `comparisons` family
- applied the exact comparison concepts and safe existing-case retags from
  sections 3.2 and 4
- replaced `lebron_durant_comparison_wave4` as the
  `player_summaries_recent_form.inverse_sibling` row with
  `tatum_brown_last10_comparison_wave4`
- expanded `public_query_acceptance` from `67` to `109` existing corpus rows
- reduced the registry from `17` to `16` families: `14` public feature
  families and `2` guardrail families
- filled every required matrix variant without adding a new query or changing
  an expectation
- marked only the five triage-approved `typo_partial_entity_behavior` variants
  as not applicable
- added at least one pending `review_required` representative card for every
  public feature family

Generated review artifact:

```text
outputs/raw_query_answer_qa/20260531T073042Z_wave2a_taxonomy_safe_retags/product_review.md
```

The matrix has no missing variants, but public acceptance remains intentionally
open. No family is public accepted, the human-review declaration remains
`human_review_pending`, the bare `LeBron vs KD` V1 policy is now a clean
ambiguous/no-result boundary, and rendered frontend review remains a separate
Wave 2C task.

### Wave 2B: Probe Batch

Goal: investigate product questions and any genuinely new user-obvious
phrasing before adding expectations.

Probe at minimum:

```text
LeBron vs KD
How do LeBron James and Kevin Durant compare this season?
Who are the MVP candidates?
who has cooled off lately
how many players played this season
most rebunds in a game this season
Lakeers playoff history
```

For each probe:

1. record route, status, reason, sections, and applied or unsupported filters
2. check for broadened scope
3. classify as safe corpus addition, behavior bug, or product decision
4. add expectations only for reviewed correct behavior

#### Wave 2B Probe And Fix Notes

Wave 2B probe results are recorded in
`working/public-query-acceptance-review/PUBLIC_QUERY_ACCEPTANCE_WAVE_2B_PROBE_RESULTS.md`.

The probe classified `How do LeBron James and Kevin Durant compare this
season?` as a behavior bug because it dropped Kevin Durant and routed to a
LeBron-only `player_game_summary`. A follow-up routing fix now routes that
question-form comparison to `player_compare`, preserves both players, and adds
the Raw QA corpus case `question_form_lebron_durant_comparison_wave2b`.

The later V1 bare player-vs-player boundary changed `LeBron vs KD`,
`LeBron James vs Kevin Durant`, and `Jokic vs Embiid` to
`player_compare / no_result / ambiguous_query`. No family is public accepted by
this fix.

### Wave 2C: Human Rendered-Output Review

Goal: review the public frontend, not only backend approximations.

Review:

- the four existing representative cards from section 5
- new representative cards added in Wave 2A
- unrouted-error rendering for subjective and typo cases
- game-log density for player and team summaries

Record one review declaration:

```text
human_review_pending
human_review_complete
human_review_complete_with_followup
```

### Follow-Up Fix Waves

Create separate PR-sized waves only for confirmed behavior defects:

1. comparison ambiguity or wrong-scope fixes
2. unsupported-concept reason/status normalization
3. route-preserving typo-boundary consistency fixes
4. frontend copy or density fixes found during rendered review

After every follow-up wave, regenerate and review:

```text
outputs/raw_query_answer_qa/<run_id>/product_review.md
```

## 8. Validation For Wave 2

Run:

```bash
.venv/bin/pytest tests/test_raw_query_answer_qa.py -n0
.venv/bin/python tools/raw_query_answer_qa.py \
  --corpus qa/raw_query_answer_corpus.yaml \
  --slice public_query_acceptance \
  --fail-on-expectation-failure
git diff --check
```

Run Markdown lint if an installed repo-local or PATH command is available.

Parser/query tests are required only for later waves that change production
behavior.

## 9. Stop Conditions

Stop Wave 2 and split out a fix or decision wave when:

- any proposed expected-ok query returns wrong scope
- any unsupported query broad-falls back
- any comparison taxonomy uncertainty remains unresolved
- any case would encode current bad behavior as expected
- any public-acceptance claim lacks human review
- any retagged no-broad-fallback case lacks scoped proof

## 10. Current Review Declaration

```text
human_review_pending
```

Wave 2A filled the metadata matrix with existing passing rows. Public frontend
rendering has not yet been human-reviewed, Wave 2B probes have not run, and no
family is public accepted.
