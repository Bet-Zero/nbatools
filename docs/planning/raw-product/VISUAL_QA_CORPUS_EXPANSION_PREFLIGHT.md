# Visual QA Corpus Expansion Preflight

## 1. Purpose

This preflight plans the next Visual QA corpus expansion after the Raw Product
public UI hardening and parser boundary cleanup work. It is docs-only. It does
not change production code, frontend rendering, backend behavior,
parser/routing behavior, result contracts, QA corpus files, or supported query
surface.

The deferred-work priority now ranks Visual QA corpus expansion immediately
after parser maintainability work. The current visual baseline is useful, but
it still reflects the earlier Wave 1 risk set: filtered leaderboards, guarded
unsupported states, and selected dense table shapes. The public/mobile result
surface now needs a small expansion for answer-first families that are already
supported and already represented in raw and frontend-copy QA.

## 2. Sources Reviewed

- `working/raw-product-post-launch/RAW_PRODUCT_POST_LAUNCH_DEFERRED_WORK_PRIORITY.md`
- `docs/operations/ui_guide.md`
- `qa/frontend_visual_qa_corpus.json`
- `qa/frontend_visual_qa_corpus.yaml`
- `frontend/src/VisualQaPage.tsx`
- `frontend/src/test/VisualQaPage.test.tsx`
- `frontend/src/visualQaCases.ts`
- `docs/operations/frontend_visual_qa.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_EVIDENCE_SUMMARY.md`
- `qa/raw_query_answer_corpus.yaml`
- `qa/frontend_copy_corpus.yaml`

## 3. Current Visual Corpus Inventory

The runtime visual corpus currently contains 15 cases. Every case requests both
`desktop_1280` and `mobile_390`, so the manual baseline is 30 viewport reviews
before notes or screenshot retakes.

| Current bucket | Count | Current case IDs | Coverage value |
| --- | ---: | --- | --- |
| Position-filtered player leaderboards | 2 | `guards_fg_percentage_leaders`, `centers_rebound_leaders_wave4` | Filter-chip placement and leaderboard metric readability. |
| Team defense leaderboards | 3 | `fewest_points_allowed_team_leader`, `most_points_allowed_team_leaders_wave4`, `opponent_ppg_leaders_wave4` | Defensive wording and long opponent-metric labels. |
| Guarded unsupported/no-result states | 5 | `personal_foul_leaders_wave4`, `rookie_scoring_leaders_wave4`, `starter_assist_leaders_wave4`, `bench_scoring_leaders_wave4`, `celtics_bench_scoring_boundary_wave4` | Product-facing no-result hierarchy and diagnostics containment. |
| Record answer surfaces | 2 | `record_when_jokic_triple_double`, `lakers_road_record_last_season` | Record hero/filter cohesion for condition and season/location filtering. |
| Playoff matchup history | 1 | `heat_knicks_playoff_series_record_wave4` | Dense postseason matchup comparison/table behavior. |
| Player comparison | 1 | `lebron_durant_comparison_wave4` | Two-subject identity and mobile comparison readability. |
| Top performances | 1 | `biggest_scoring_games` | Dense top-performance table and outlier-row readability. |

Current implementation notes:

- `frontend/src/visualQaCases.ts` imports
  `qa/frontend_visual_qa_corpus.json` for the page.
- The companion YAML corpus and the Wave 1 checklist still document the same
  15-case baseline.
- `frontend/src/VisualQaPage.tsx` renders the public result surface with
  internal case metadata, but its hero copy still says "15 approved visual QA
  cases".
- `frontend/src/test/VisualQaPage.test.tsx` hardcodes the approved ID list and
  the 15-case completion/count expectations.

## 4. Coverage Gaps

The current corpus covers important Wave 1 regressions, but it is not balanced
across the answer-first public/mobile families named in the UI guide and the
final public UI release review.

| Public/mobile family | Current visual corpus state | Why it matters now |
| --- | --- | --- |
| Player season summary | Missing | Short answer-first summary surfaces need a hero hierarchy check that is not driven by wide tables. |
| Count plus player finder/game log | Missing | The count hero and capped wide game log stress answer-first order, filter context, and mobile internal scrolling together. |
| Player split | Missing | Split chips, labels, table priorities, and details toggles are distinct from comparison and record tables. |
| Player streak | Missing | Threshold condition, span/status, and compact streak detail have their own mobile density risks. |
| Rolling stretch | Missing | Window, metric, date span, and rolling table columns are not represented in the current visual set. |
| Single-team playoff history | Under-covered | The corpus has playoff matchup history, but not the long single-team playoff-history route. The final public release review already spot-checked this query on desktop/mobile. |

The release review manually passed the same supported public queries proposed
for the missing families. That manual smoke evidence is useful, but it is not a
repeatable `/visual-qa` baseline. The first expansion should turn the five
fully missing families into visual corpus cases without reopening parser or
renderer work.

## 5. Candidate Coverage Check

None of the five recommended core cases is already present in the visual corpus.
All six known candidates already exist elsewhere in supported QA or manual
review evidence.

| Candidate label | Existing source coverage | Existing visual/release evidence | Preflight decision |
| --- | --- | --- | --- |
| `jokic_season_summary` | Raw QA and frontend-copy QA use the same ID. | Final public UI release review checked `Jokic this season`. | Add. |
| `jokic_triple_double_finder` | Raw QA and frontend-copy QA already cover the same query as `jokic_triple_double_count`. | Final public UI release review checked the count/finder query. | Add with the visual ID below. |
| `jokic_home_away_split` | Raw QA and frontend-copy QA use the same ID. | Final public UI release review checked the split query. | Add. |
| `curry_3_threes_streak` | Raw QA and frontend-copy QA use the same ID. | Final public UI release review checked the streak query. | Add. |
| `jokic_best_5_rebounding_stretch` | Raw QA and frontend-copy QA already cover the same query as `jokic_5_game_rebound_stretch`. | Final public UI release review checked the rolling-stretch query. | Add with the visual ID below. |
| `lakers_playoff_history` | Raw QA and frontend-copy QA use the same ID. | Final public UI release review checked the single-team playoff-history query; current visual corpus already has playoff matchup history. | Defer from this first expansion wave. |

## 6. Recommended Execution Wave

### 6.1 Scope

Add five cases:

1. `jokic_season_summary`
2. `jokic_triple_double_finder`
3. `jokic_home_away_split`
4. `curry_3_threes_streak`
5. `jokic_best_5_rebounding_stretch`

That grows the manual baseline from 15 to 20 cases and from 30 to 40 required
desktop/mobile viewport reviews. The increase is material but still bounded:
it adds one representative case for each currently missing high-value result
family instead of adding multiple player/team variants at once.

Do not add new unsupported/no-result cases in this wave. The current visual
corpus already spends 5 of 15 cases on guarded unsupported states, and the
next priority is supported public/mobile result coverage.

### 6.2 Exact Corpus Entries

Use the following case objects in the execution wave. Add the same five entries
to the JSON runtime corpus and the companion YAML corpus, preserving the
existing corpus field shape and the two required viewports.

```json
{
  "id": "jokic_season_summary",
  "category": "player_summary",
  "query": "Jokic this season",
  "viewports": ["desktop_1280", "mobile_390"],
  "visual_focus": [
    "Player-summary hero reads as the primary answer before supporting detail",
    "Nikola Jokic identity and season context stay clear without relying on a wide table",
    "Secondary actions and details stay visually downstream from the summary answer"
  ],
  "desktop_focus": [
    "Hero stats and player identity align cleanly in the summary surface",
    "Supporting summary/detail content does not compete with the answer sentence"
  ],
  "mobile_focus": [
    "Summary hero remains readable before lower-priority detail on a 390px viewport",
    "Identity, key stats, and available context wrap without clipping or crowding"
  ],
  "expected_primary_visual_concerns": [
    "Short summary answers can feel visually thin if the hero and detail hierarchy drift",
    "Mobile summary stats or identity treatment can wrap into an unclear answer block"
  ]
}
```

```json
{
  "id": "jokic_triple_double_finder",
  "category": "count_with_finder",
  "query": "How often has Nikola Jokic recorded a triple-double this season?",
  "viewports": ["desktop_1280", "mobile_390"],
  "visual_focus": [
    "Count answer appears before the finder game log",
    "Triple-double filter context stays tied to the count and the first finder rows",
    "Wide game-log detail remains visibly contained after the answer"
  ],
  "desktop_focus": [
    "Count hero, special-event context, and first finder rows read in one scan",
    "Date, opponent, and core stat columns remain easy to inspect in the game log"
  ],
  "mobile_focus": [
    "Count hero and Triple Double context remain visible before horizontal table detail",
    "Finder/game-log scrolling stays internal and the first row does not clip the page"
  ],
  "expected_primary_visual_concerns": [
    "A dense finder table can visually overtake the count answer",
    "Mobile game-log width can hide context or widen the page if containment regresses"
  ]
}
```

```json
{
  "id": "jokic_home_away_split",
  "category": "player_split",
  "query": "Jokic home vs away this season",
  "viewports": ["desktop_1280", "mobile_390"],
  "visual_focus": [
    "Split answer and Home/Away context read before the detailed comparison rows",
    "Split labels, key columns, and details toggle stay understandable together",
    "Wide split metrics remain contained without flattening the answer hierarchy"
  ],
  "desktop_focus": [
    "Hero, split context, and comparison table align as one public answer",
    "Home and Away rows stay easy to compare across primary metrics"
  ],
  "mobile_focus": [
    "Split context wraps cleanly above the table on a 390px viewport",
    "Primary split columns stay readable before lower-priority metrics and detail"
  ],
  "expected_primary_visual_concerns": [
    "Split context can become detached from the table when chips wrap",
    "Metric-heavy split tables can become dense or rely too heavily on hidden detail"
  ]
}
```

```json
{
  "id": "curry_3_threes_streak",
  "category": "player_streak",
  "query": "Curry longest streak with at least 3 threes",
  "viewports": ["desktop_1280", "mobile_390"],
  "visual_focus": [
    "Streak condition and length read as the answer before support rows",
    "Three-point threshold context remains obvious beside span and status detail",
    "Streak table density stays readable in public mode"
  ],
  "desktop_focus": [
    "Condition, length, status/span, and first detail row scan cleanly together",
    "Threshold metric labels remain semantically aligned with the streak hero"
  ],
  "mobile_focus": [
    "Condition and streak length stay readable when threshold text wraps",
    "Start/end/status detail remains usable without forcing document-level overflow"
  ],
  "expected_primary_visual_concerns": [
    "Threshold text and span detail can compete with the primary streak answer",
    "Compact streak tables can become cramped on mobile"
  ]
}
```

```json
{
  "id": "jokic_best_5_rebounding_stretch",
  "category": "rolling_stretch",
  "query": "Jokic best 5-game rebounding stretch this season",
  "viewports": ["desktop_1280", "mobile_390"],
  "visual_focus": [
    "Window size, rebound metric, and best stretch result read as one answer",
    "Rolling-stretch date span remains clear before detailed rows",
    "Named-player stretch table density stays usable in public mode"
  ],
  "desktop_focus": [
    "Best-window hero and first ranked stretch row align without ambiguity",
    "Window, RPG, Start, and End detail remains easy to scan"
  ],
  "mobile_focus": [
    "Five-game window and rebound metric stay visible before table detail",
    "Rolling-stretch table scroll/priority behavior keeps date span readable at 390px"
  ],
  "expected_primary_visual_concerns": [
    "Window, metric, and date span can fragment into separate-looking facts",
    "Rolling-stretch rows can become hard to compare when mobile density regresses"
  ]
}
```

### 6.3 Manual QA Load

The recommended 20-case baseline is the stop point for the first execution
wave. It keeps the manual pass bounded while filling the highest-value holes.

| Baseline | Cases | Required viewports | Change |
| --- | ---: | ---: | --- |
| Current | 15 | 30 | Existing accepted manual baseline. |
| Recommended execution | 20 | 40 | Adds 10 viewport reviews for five absent supported families. |
| With optional Lakers playoff history | 21 | 42 | Adds a partially adjacent playoff-history variant; defer for now. |

## 7. Deferred and Rejected Cases

| Case or bucket | Decision | Reason |
| --- | --- | --- |
| `lakers_playoff_history` | Defer | Valuable single-team postseason coverage, but the current corpus already has playoff matchup history and the final public release review explicitly passed the single-team query. Add it in a later visual pass if playoff-history polish becomes active or screenshot automation needs both postseason modes. |
| Extra unsupported/no-result cases | Reject for this wave | Unsupported boundaries are already heavily represented in the 15-case corpus. |
| Multiple streak or split variants | Defer | The first expansion needs renderer-family representation, not exhaustive player/team permutations. |
| New query support or new result contracts | Out of scope | Visual corpus expansion must use already supported results only. |

## 8. Frontend-Copy QA Impact

No frontend-copy corpus or frontend-copy harness update is recommended for the
Visual QA execution wave:

- All five recommended queries are already covered in `qa/frontend_copy_corpus.yaml`.
- The optional Lakers playoff-history candidate is already covered there too.
- The Visual QA addition should not change public result copy, result
  contracts, or rendering behavior.

The execution wave should keep provenance accurate. The current visual corpus
still names an older frontend-copy report. If the execution wave relies on the
current 125-case frontend-copy coverage for the new finder, streak, and
rolling-stretch entries, refresh the visual corpus source metadata to a report
that contains those selected cases rather than implying the older source run
covered them.

Stop and split work if the corpus addition exposes a user-visible copy problem
that requires frontend-copy expectations or public copy to change.

## 9. Visual QA Page and Test Impact

Visual QA page tests need updates in the execution wave.

Expected updates:

1. Update `qa/frontend_visual_qa_corpus.json` and
   `qa/frontend_visual_qa_corpus.yaml` with the five case objects and any
   source-run metadata refresh.
2. Update `frontend/src/test/VisualQaPage.test.tsx` for the approved case ID
   list and the new 20-case count expectations.
3. Update the literal 15-case wording in `frontend/src/VisualQaPage.tsx` so
   the internal page does not describe a stale corpus size.
4. Update the referenced visual checklist path/content in the execution wave
   if the accepted Wave 1 checklist should remain immutable. Do not leave a
   page pointing at a checklist that claims only 15 cases when the route shows
   20.

No `ResultRenderer`, backend, parser, route, or result-contract change is
expected.

## 10. Execution Plan

1. Add the five recommended entries to both visual corpus files and refresh
   source-run metadata if the new cases use a newer frontend-copy provenance
   report.
2. Keep the change limited to visual QA corpus/page/test/checklist artifacts.
3. Update `VisualQaPage` internal copy and `VisualQaPage` tests for the new
   corpus size and ID set.
4. Run the Visual QA page test and frontend build because frontend source will
   change.
5. Run `/visual-qa` manually at `desktop_1280` and `mobile_390`; record pass or
   blocker notes for the five new cases and confirm the existing 15 cases still
   load.
6. Leave screenshot-diff automation for the separately ranked follow-up item.

## 11. Validation Plan

Recommended execution validation:

```bash
cd frontend && npm test -- src/test/VisualQaPage.test.tsx
```

```bash
cd frontend && npm run build
```

```bash
git diff --check
```

For docs changed in the execution wave, run markdown lint if an available
repo-local or installed markdown lint command is present. If no command is
available, record that result in the return package.

Manual validation:

- `/visual-qa` loads all 20 live cases with request errors called out.
- Desktop around `1280px` and mobile around `390px` are reviewed for the five
  new cases using the focus text in section 6.2.
- The page still renders the public result surface, not debug-only result
  chrome, while retaining internal case metadata and capture wrappers.

## 12. Stop Conditions

Stop the execution wave and return to planning if any of these happen:

- A recommended case requires parser, routing, backend, contract, or production
  result-renderer changes to produce the intended supported answer.
- A new case is not present in the selected raw/frontend-copy QA source used
  as provenance for the execution wave.
- Any new case loads as a backend error, unexpected unsupported state, request
  error, or materially misleading answer.
- Manual scope grows beyond the recommended 20-case baseline without a
  deliberate decision to expand review load.
- The optional Lakers playoff-history case becomes necessary to resolve a real
  postseason renderer risk; handle that as an explicit scope decision rather
  than an incidental sixth add.
