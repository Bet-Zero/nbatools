# Front-Facing Result UI Productization Preflight Return Package

## 1. Executive summary

- Recommended decision: productize the default `/` result surface before broad
  public launch, while keeping the current debug-rich rendering available for
  `/review`, `/visual-qa`, and explicit debug mode.
- Main issue: the result patterns are already answer-first, but the surrounding
  default UI still exposes route names, query classes, backend status/reason,
  raw JSON, structured-query tooling, QA-oriented sample hints, and verbose
  note/detail blocks before or around the answer.
- Best UI strategy: keep the current engine contracts and result patterns, add
  a front-facing display mode at the app/result-envelope level, and move debug
  metadata into a progressive Details drawer.
- Should public launch wait for this? yes for a broad public/final-product
  launch; no for limited preview, handoff, or feedback collection.
- Production code changed? no.
- Tests changed? no.
- Corpus changed? no.

The release candidate remains technically strong. Raw QA is 246/246 passing,
frontend-copy QA is 125/125 passing, preview is ready with notes, feedback is
ready with notes, and the feedback review/export workflow is implemented. This
preflight identifies a presentation/product polish gap, not an engine
correctness blocker.

## 2. Current debug-heavy surfaces

| UI element | Current location | Public default recommendation | Details/debug recommendation |
|---|---|---|---|
| Result panel title `Query output` | `frontend/src/App.tsx` result actions card | Replace with quieter action row or omit; the answer hero should be the first result signal. | Keep in `/review` if useful as a section label. |
| Status badge `Success` / `No Result` / `Error` | `ResultEnvelope` meta | Hide for successful answers; no-result/error states should use public copy, not raw status badges. | Show raw `result_status` in Details and `/review`. |
| Route badge | `ResultEnvelope` meta and history items | Hide from default public result. | Show route in Details, `/review`, `/visual-qa`, history debug mode, and feedback payloads. |
| Query class badge | `ResultEnvelope` meta and history items | Hide from default public result. | Show query class in Details and `/review`; retain in feedback payloads. |
| Result reason text | `ResultEnvelope` meta and `NoResultDisplay` | Translate to user copy only when needed. Do not show `filter_not_supported`, `unrouted`, or similar strings by default. | Show raw `result_reason` in Details and `/review`. |
| Data-through/current-through date | `ResultEnvelope` meta and `FreshnessStatus` | Show only as compact freshness context when material, stale, or requested; otherwise move out of the main answer path. | Keep exact `current_through`, freshness detail, and per-season rows in Details/debug. |
| Query echo | `ResultEnvelope` query line | Optional small "You asked" context only after the primary answer, or inside Details. | Keep full query in Details, Copy Query, history, `/review`, and feedback records. |
| Player/team/season/opponent/split chips | `ResultEnvelope` context chips | Keep visible by default when they describe the user's requested scope. | Details can include raw metadata and resolved entity ids. |
| Applied filter chips | `ResultEnvelope` context chips | Keep only user-meaningful filters: season, date window, home/away, last N, opponent group/conference, playoffs/regular season, threshold, without-player. Polish labels. | Show raw applied filters with `kind`, original label/value, and parser-derived fields in Details/debug. |
| Context info block | `ResultEnvelope` notices/context block | Avoid duplicating chips. Show only material interpretation changes or necessary disambiguation. | Move `Interpreted as`, metric, aggregation, date range, included-opponent counts, and raw context into Details. |
| Notes block | `ResultEnvelope` notices | Hide nonmaterial notes by default. Show only product-facing notes that change user trust or interpretation. | Keep all sanitized notes in Details and `/review`. |
| Caveats block | `ResultEnvelope` notices | Keep material caveats visible, but make them concise and human. | Keep raw caveats and original backend wording in Details/debug. |
| Alternates / did-you-mean chips | `ResultEnvelope` alternates | Keep visible for ambiguity or no-result recovery. | Keep full alternate route/confidence information in Details/debug if exposed later. |
| Copy Link | `App.tsx` result actions | Keep visible or place in a compact action menu. | Same in debug. |
| Copy Query | `App.tsx` result actions | Move behind an action menu or Details; not part of the primary answer. | Keep visible in debug/review. |
| Copy JSON | `App.tsx` result actions | Hide from default public UI. | Keep in Details/debug and `/review`. |
| Save Query | `App.tsx` result actions | Keep as a secondary public action if saved queries remain part of product. | Same in debug. |
| Report issue / Submit for review | `App.tsx`, `ResultRenderer`, `NoResultDisplay` | Keep visible, especially for no-result/unsupported states. | Keep payload metadata intact even when metadata is hidden visually. |
| Raw response panel | `RawJsonToggle` | Hide from default public UI. | Keep as Details/debug output and `/review` support. |
| Raw/additional table toggles | `RawDetailToggle` in patterns | Keep extra columns behind public "Show more details" labels; avoid "raw table" language. | Keep full raw/detail tables in review/debug. |
| Fallback raw section cards | `FallbackTableResult` | Avoid as a first-class public surface for known shipped routes. If encountered, put behind Details or present as a generic detail table. | Keep fallback table behavior in `/review` so unmapped routes are inspectable. |
| No-result status badge and `Why this happened` block | `NoResultDisplay` | Public state should lead with a plain message, suggestions, and feedback. Hide backend-style notes by default. | Details should show route, reason, unsupported filters, notes, caveats, and metadata. |
| Unsupported boundary codes | No-result notes/caveats and metadata | Do not show codes such as `personal_foul_leaderboard` by default. Explain the unsupported family in plain language. | Show exact `unsupported_filters` and blocked codes in Details/debug. |
| Structured-query Dev Tools | `DevTools` in default sidebar | Hide from default public UI. | Keep behind `debug=1`, `/review`, or another internal/developer affordance. |
| Starter-query result hints | `SampleQueries` | Remove route/pattern hints such as `entity_summary + game_log` and `fallback_table` from public starter buttons. | Keep renderer hints in `/review` or debug mode if useful. |
| History route/query-class badges | `QueryHistory` | Show query text and time/status only, or hide route/query-class labels. | Keep route/query-class labels in debug mode. |
| API online/version badge | `App.tsx` header | Show only user-relevant offline/error state. Hide version by default. | Keep version/API status in Details/debug or internal pages. |
| Freshness expanded operational detail | `FreshnessStatus` | Keep compact freshness only when useful; avoid operational refresh errors in normal result flow unless trust is affected. | Keep exact season coverage, refresh timestamps, and errors in Details/debug. |
| Confidence/intent | API envelope and feedback payloads, not normal UI except raw JSON | Keep hidden from public. | Preserve in Details/raw JSON/review and feedback payloads. |

## 3. Proposed display modes

| Mode | Audience | Shows | Hides |
|---|---|---|---|
| `public` default | Normal product users on `/` | Primary answer hero, user-meaningful context chips, polished result table/cards, material caveats, Copy Link, Save Query if retained, Report issue/Submit for review. | Route, query class, raw status/reason, confidence, intent, raw JSON, structured-query tools, QA fixture labels, backend note codes. |
| `public details` drawer | Users who need provenance or troubleshooting context | Data-through date, applied filters, resolved entities, caveats/notes, copied query, raw status/reason, route, query class, and optional JSON/export actions. | Nothing important is removed; it is just progressively disclosed. |
| `review/debug` | Developer, parser, QA, release review | Current route/status/query-class/raw metadata behavior, full notes/caveats, raw/additional tables, Copy JSON, route and shape labels, fixture metadata. | No supported debug capability should be hidden here. |
| `/visual-qa` | Internal visual QA | Current visual case metadata plus rendered result. Initially test public rendering; later allow public/debug side-by-side or a mode toggle. | Should not send feedback records and should remain internal. |

Implementation note: `details` should be a disclosure state inside `public`,
not a separate route contract. The code can still model it as a display-mode
variant if that is cleaner, but the user experience should be "public answer
with Details available."

## 4. Result envelope proposal

- Primary answer: use the existing `ResultHero` output from the result pattern
  as the first visible result content. Example: "Boston went 36-16 against
  Eastern Conference teams."
- Context chips: show only user-meaningful scope chips by default: Season,
  Team, Player, Opponent, Opponent conference, Opponent group, Home/away, Date
  window, Last N, Playoffs/regular season, Threshold, Without player, Split.
- Result body: keep the existing pattern-specific tables/cards, with row caps
  and horizontal table scrolling. Continue to avoid client-side business logic.
- Caveats: show material caveats inline near the answer. Move nonmaterial notes
  and backend-detail wording into Details.
- Details drawer: include route, result status, result reason, query class,
  current-through, applied filters, resolved entities/opponents, raw metadata,
  notes, caveats, Copy Query, Copy JSON, Raw JSON, and any additional/raw
  tables.
- Feedback action: keep public, especially for no-result, unsupported, and
  wrong-answer cases. The feedback payload should continue carrying hidden
  metadata so reports remain actionable.

Recommended structure on `/`:

1. Result action row: Copy Link, Save Query, Report issue.
2. Primary answer and result body from `ResultRenderer`.
3. Compact context chip bar.
4. Material caveat, if any.
5. Details drawer.

The exact order can be tested visually, but the primary answer should not sit
below route/status/debug chrome.

## 5. Result-family recommendations

| Result family | Public headline/body | Details/debug content | Mobile notes |
|---|---|---|---|
| `LeaderboardResult` | Headline should state the leader and metric. Body should show rank, player/team, metric, and only the most useful supporting columns such as GP, season, or qualifier. | Route, query class, stat key, qualification/minimums, raw ids, source notes, and full raw leaderboard columns. | Keep rank, entity, and metric as primary columns. Defensive metrics need clear labels such as Opp PPG or Points Allowed. |
| `RecordResult` | Headline should be a sentence such as "Boston went 36-16 against Eastern Conference teams." Body should show Team, W-L, GP, Win %, PPG, plus/minus, and the requested opponent/location filter when useful. | Raw route/status, date/current-through, applied filters, opponent entity resolution, by-season/detail tables, game ids. | Record and scope must remain visible before secondary columns. Chips should wrap without pushing the record below the fold. |
| `GameLogResult` | Headline should use `answer_phrase`/`count_phrase` when present. Body should show date, team, opponent, W/L, score, and requested stats. | Full game rows, game ids, hidden player/team ids, raw detail sections, route and query class. | Keep row cap in public mode. Date/opponent/result/requested stat should be primary; secondary stats can hide or scroll. |
| `TopPerformancesResult` | Headline should identify the top performance and metric. Body should show rank, player/team, date, opponent, result, score, requested metric, and a few supporting stats. | Raw stat key, season/date filters, ids, unsupported fallback notes if any, full stat columns. | Rank, entity, date, and metric are primary. Long team/player names and score cells need fixed sizing. |
| `ComparisonResult` | Headline should summarize the edge or head-to-head record. Body should use subject panels plus a compact metric table with the most important metrics first. | `head_to_head_used`, route, query class, raw summary/comparison rows, hidden metrics, resolved entity ids. | Stack subject panels. Keep "Show more metrics" public, but raw comparison rows belong in Details. |
| `PlayoffHistoryResult` | Headline should state appearances, record, round, or series lead. Body should show season/round/opponent/result/record depending on mode. | Round-data caveats, pre-2001 round limitations, route, raw summary/comparison rows, team ids. | Preserve round and season context. Material historical caveats should stay visible but concise. |
| `StreakResult` | Headline should state active/completed status, condition, length, and span. Body should show entity, condition, length, status, start/end, and requested average. | Raw condition codes, route, min streak length, ids, full streak detail columns. | Condition and length should be primary. Long threshold wording should wrap cleanly. |
| `RollingStretchResult` | Headline should describe the best window, metric, player, and timeframe. Body should show rank/player/window/value/start/end/season, plus best-window games for named-player results. | Raw window ids, stretch display mode, dedupe behavior, full game rows, metric keys. | Window and metric value must remain adjacent. Limit supporting columns on phone widths. |
| `SplitResult` | Headline should state the entity and split context. Body should show bucket, GP, record, and core stats; edge chips can remain public. | Bucket keys, raw split summary, route, query class, full detail rows. | Two-bucket tables should stay compact. Edge chips should wrap after the table, not crowd it. |
| `EntitySummaryResult` | Headline is already close to public-ready for player summaries and record-when cases. Body should show by-season only when it supports the requested scope. | Scope kind, raw summary row, applied filters, ids, by-season raw detail. | Avoid duplicating a summary table when the hero already answers the query. |
| `FallbackTableResult` | Avoid as a default public shape for shipped routes. If a fallback appears, present it as "Detailed results" rather than raw section keys. | Keep existing raw section cards in `/review` for unmapped route inspection. | Fallback tables can be wide; keep internal scrolling and avoid letting them widen the shell. |
| `NoResultDisplay` | Plain message first: "NBA Tool does not support personal-foul leaderboards yet." Then suggestions and Submit for review. | Raw status/reason, unsupported filters, notes, caveats, route, query class, candidates, suggested queries, metadata. | The primary message must stay above diagnostics; Details should not push the message below the first viewport. |

## 6. No-result/unsupported UX recommendation

- Public copy: lead with the product boundary or recovery path in plain
  language. Examples:
  - "NBA Tool does not support personal-foul leaderboards yet."
  - "No NBA games matched Apr 11, 2026."
  - "I could not interpret \"cooled off\" as a supported stat query yet."
- Details copy: show `route=season_leaders`,
  `reason=filter_not_supported`, `unsupported_filters=personal_foul_leaderboard`,
  notes, caveats, and suggested internal routing context.
- Feedback action: keep "Submit for review" visible for unsupported/no-result
  states and keep "Report issue" for successful answers.
- Guardrails:
  - Do not hide material unsupported-boundary guidance.
  - Do not show raw backend codes in the default public message.
  - Do not imply unsupported families are supported.
  - Do not remove feedback metadata from issue payloads.
  - Do not auto-convert feedback into corpus changes.

## 7. Implementation options

| Option | Scope | Value | Risk | Recommendation |
|---|---|---|---|---|
| A. Add only a `ResultEnvelope` prop | Hide route/status/reason and notes from the envelope in public mode. | Smallest change. | Leaves Raw JSON, Copy JSON, DevTools, sample hints, no-result diagnostics, and review preservation scattered. | Not enough alone. |
| B. App-level display mode plus component props | Derive mode at app/page level, pass to `ResultEnvelope`, `ResultRenderer`, `NoResultDisplay`, result actions, `RawJsonToggle`, sidebar tools, and QA pages. | Cleanest separation; preserves debug paths and allows URL debug mode. | Requires several small coordinated edits and tests. | Recommended. |
| C. URL-only `?debug=1` toggles current UI | Keep public default clean and expose debug chrome with a shareable URL param. | Useful for support and development. | If implemented alone, page-specific defaults may drift. | Use as part of Option B. |
| D. Environment flag only | Hide debug UI in production builds. | Simple deployment behavior. | Not shareable, harder to QA, and risky for support. | Avoid as the primary control. |
| E. Separate public result components | Build a new public result tree and leave current one for review. | Maximum freedom. | High duplication and high chance of contract drift. | Avoid for this phase. |
| F. CSS-only hiding | Hide badges/actions visually without changing structure. | Very small change. | Brittle, accessibility risk, and leaves debug semantics in the DOM. | Avoid. |

Cleanest approach: Option B with a URL debug escape hatch. `/` defaults to
`public`; `/review` forces `review/debug`; `/visual-qa` initially renders
`public` while keeping case metadata, then can add a public/debug comparison
toggle in a later visual QA wave.

## 8. Recommended execution plan

- Wave 1: Add display mode and Details drawer. Move obvious debug fields out of
  public default: route, query class, result reason, Copy JSON, Raw JSON, raw
  notes, DevTools, starter-query renderer hints, and history route badges.
- Wave 2: Polish public headlines/context placement for the main result
  families. Keep existing `ResultHero` and tables; focus on envelope ordering,
  context chips, caveats, and action hierarchy.
- Wave 3: No-result public UX polish. Translate unsupported/raw reason details
  into clean public copy and move raw diagnostic notes behind Details.
- Wave 4: Mobile polish pass and visual QA baseline refresh, including public
  default and debug/review screenshots.
- Wave 5: Optional user/developer preference or explicit debug toggle if the
  URL param is not enough.

Files likely to change:

- `frontend/src/App.tsx`
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/components/NoResultDisplay.tsx`
- `frontend/src/components/results/ResultRenderer.tsx`
- `frontend/src/components/results/primitives/RawDetailToggle.tsx`
- `frontend/src/components/RawJsonToggle.tsx`
- `frontend/src/components/DevTools.tsx`
- `frontend/src/components/SampleQueries.tsx`
- `frontend/src/components/QueryHistory.tsx`
- `frontend/src/ReviewPage.tsx`
- `frontend/src/VisualQaPage.tsx`
- `frontend/src/test/*`
- `qa/frontend_copy_corpus.yaml`
- `qa/frontend_visual_qa_corpus.json`
- `docs/operations/ui_guide.md`

Tests to update/add:

- Result envelope tests for public vs review/debug mode.
- No-result tests for public copy plus Details metadata.
- App/first-run tests for absence of `Query output`, route badges, Copy JSON,
  Raw JSON, and DevTools in public mode.
- Review page tests proving debug rendering remains available.
- Visual QA page tests proving the route still loads and can render the chosen
  mode.
- Frontend-copy QA corpus updates for public copy expectations.

QA validation:

- `cd frontend && npm test -- src/test/<targeted files>`
- `cd frontend && npm run qa:frontend-copy`
- `cd frontend && npm run build`
- `cd frontend && npm run lint`
- Preview smoke of `/`, `/review`, and `/visual-qa`
- Visual QA baseline refresh after public/default UI changes

No backend raw QA is needed if result contracts, parser behavior, and backend
query behavior are unchanged. Run backend raw QA only if implementation changes
contracts or backend behavior, which this plan should avoid.

Stop conditions:

- Any result contract change is proposed.
- Any parser/backend behavior change becomes necessary.
- `/review` loses route/status/raw metadata needed for QA.
- `/visual-qa` loses internal case metadata or screenshot capture utility.
- Unsupported-boundary guidance becomes less visible or less accurate.
- Feedback payloads lose route, reason, query class, confidence, current-through,
  metadata, notes, or caveats.

## 9. Release impact

- Current engine readiness: strong release candidate with notes; raw QA
  246/246 passing and supported/unsupported boundaries documented.
- Current UI readiness: preview-ready with notes and frontend-copy QA clean, but
  not yet ideal as a final front-facing public result surface because default
  `/` still exposes development and QA chrome.
- Launch recommendation: continue preview/feedback use; productize Wave 1 and
  Wave 3 before broad public launch. Wave 2 should follow quickly for polish,
  but Wave 1 plus no-result cleanup is the minimum public-facing threshold.
- What must be done before public launch:
  - Public default mode hides raw route/status/reason/query-class/debug JSON.
  - Details drawer preserves metadata, caveats, applied filters, and raw JSON.
  - `/review` remains debug-rich.
  - `/visual-qa` remains useful and can validate the public surface.
  - No-result/unsupported copy is plain-language and still guarded.
  - Frontend-copy and visual QA baselines are updated intentionally.

## 10. Validation performed

Files inspected:

- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md`
- `docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md`
- `docs/operations/ui_guide.md`
- `frontend/src/App.tsx`
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/components/NoResultDisplay.tsx`
- `frontend/src/components/noResultDisplayUtils.ts`
- `frontend/src/components/RawJsonToggle.tsx`
- `frontend/src/components/DevTools.tsx`
- `frontend/src/components/QueryFeedback.tsx`
- `frontend/src/components/queryFeedbackPayload.ts`
- `frontend/src/components/QueryHistory.tsx`
- `frontend/src/components/FreshnessStatus.tsx`
- `frontend/src/components/SampleQueries.tsx`
- `frontend/src/components/SavedQueries.tsx`
- `frontend/src/components/EmptyState.tsx`
- `frontend/src/components/AppShell.tsx`
- `frontend/src/design-system/ResultEnvelopeShell.tsx`
- `frontend/src/components/results/ResultRenderer.tsx`
- `frontend/src/components/results/config/routeToPattern.ts`
- `frontend/src/components/results/patterns/LeaderboardResult.tsx`
- `frontend/src/components/results/patterns/RecordResult.tsx`
- `frontend/src/components/results/patterns/GameLogResult.tsx`
- `frontend/src/components/results/patterns/TopPerformancesResult.tsx`
- `frontend/src/components/results/patterns/ComparisonResult.tsx`
- `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx`
- `frontend/src/components/results/patterns/StreakResult.tsx`
- `frontend/src/components/results/patterns/RollingStretchResult.tsx`
- `frontend/src/components/results/patterns/SplitResult.tsx`
- `frontend/src/components/results/patterns/EntitySummaryResult.tsx`
- `frontend/src/components/results/patterns/FallbackTableResult.tsx`
- `frontend/src/components/results/primitives/RawDetailToggle.tsx`
- `frontend/src/components/results/primitives/ResultHero.tsx`
- `frontend/src/components/results/primitives/ResultTable.tsx`
- `frontend/src/ReviewPage.tsx`
- `frontend/src/VisualQaPage.tsx`
- `frontend/src/api/types.ts`
- `frontend/src/test/frontendCopyQaHarness.tsx`
- `qa/frontend_copy_corpus.yaml`
- `qa/frontend_visual_qa_corpus.json`
- `outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md`
- `return_packages/raw-product/FRONTEND_COPY_QA_EXPANSION_WAVE_2_RETURN_PACKAGE.md`
- `return_packages/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF_RETURN_PACKAGE.md`

Commands/probes run:

```bash
git status --short
sed -n '1,220p' docs/planning/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF.md
sed -n '1,260p' docs/planning/raw-product/RAW_PRODUCT_RELEASE_PACKAGE.md
sed -n '1,260p' docs/operations/ui_guide.md
sed -n '1,260p' frontend/src/App.tsx
sed -n '260,620p' frontend/src/App.tsx
sed -n '620,920p' frontend/src/App.tsx
sed -n '1,260p' frontend/src/components/ResultEnvelope.tsx
sed -n '260,620p' frontend/src/components/ResultEnvelope.tsx
sed -n '620,980p' frontend/src/components/ResultEnvelope.tsx
sed -n '1,260p' frontend/src/components/NoResultDisplay.tsx
sed -n '260,620p' frontend/src/components/NoResultDisplay.tsx
sed -n '1,260p' frontend/src/components/noResultDisplayUtils.ts
sed -n '260,620p' frontend/src/components/noResultDisplayUtils.ts
rg --files frontend/src/components/results/patterns frontend/src/components/results/primitives frontend/src/components/results/config
sed -n '1,260p' frontend/src/components/results/primitives/RawDetailToggle.tsx
sed -n '1,260p' frontend/src/components/results/primitives/ResultHero.tsx
sed -n '1,340p' frontend/src/components/results/primitives/ResultTable.tsx
sed -n '1,260p' frontend/src/components/results/ResultRenderer.tsx
sed -n '1,300p' frontend/src/components/results/config/routeToPattern.ts
sed -n '300,620p' frontend/src/components/results/config/routeToPattern.ts
sed -n '1,320p' frontend/src/components/results/patterns/LeaderboardResult.tsx
sed -n '1,340p' frontend/src/components/results/patterns/RecordResult.tsx
sed -n '1,360p' frontend/src/components/results/patterns/GameLogResult.tsx
sed -n '1,340p' frontend/src/components/results/patterns/TopPerformancesResult.tsx
sed -n '1,360p' frontend/src/components/results/patterns/ComparisonResult.tsx
sed -n '1,360p' frontend/src/components/results/patterns/PlayoffHistoryResult.tsx
sed -n '1,360p' frontend/src/components/results/patterns/StreakResult.tsx
sed -n '1,360p' frontend/src/components/results/patterns/RollingStretchResult.tsx
sed -n '1,380p' frontend/src/components/results/patterns/SplitResult.tsx
sed -n '1,380p' frontend/src/components/results/patterns/EntitySummaryResult.tsx
sed -n '1,280p' frontend/src/components/results/patterns/FallbackTableResult.tsx
sed -n '1,320p' frontend/src/ReviewPage.tsx
sed -n '320,700p' frontend/src/ReviewPage.tsx
sed -n '1,340p' frontend/src/VisualQaPage.tsx
sed -n '340,720p' frontend/src/VisualQaPage.tsx
sed -n '1,260p' qa/frontend_copy_corpus.yaml
sed -n '1,260p' qa/frontend_visual_qa_corpus.json
sed -n '1,260p' outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md
sed -n '1,260p' return_packages/raw-product/FRONTEND_COPY_QA_EXPANSION_WAVE_2_RETURN_PACKAGE.md
sed -n '1,260p' return_packages/raw-product/RAW_PRODUCT_RELEASE_CANDIDATE_HANDOFF_RETURN_PACKAGE.md
rg -n "route|result_status|result_reason|query_class|metadata|Raw JSON|Copy JSON|Copy Query|Query output|Data through|Applied filters|Result status|unsupported_filters|confidence|intent|query class|current_through|details|Why this happened|Result details" frontend/src qa/frontend_copy_corpus.yaml qa/frontend_visual_qa_corpus.json outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md
rg -n "no_result|filter_not_supported|unsupported|No-result|Unsupported|Why this happened|Submit for review|Report issue" qa/frontend_copy_corpus.yaml qa/frontend_visual_qa_corpus.json outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md frontend/src/components
rg -n "displayMode|RawDetailToggle|ResultEnvelope|ResultRenderer|RawJsonToggle|DevTools|QueryFeedbackButton" frontend/src
sed -n '1,300p' frontend/src/components/QueryFeedback.tsx
sed -n '1,260p' frontend/src/components/queryFeedbackPayload.ts
sed -n '1,220p' frontend/src/components/RawJsonToggle.tsx
sed -n '1,220p' frontend/src/components/DevTools.tsx
sed -n '1,220p' frontend/src/design-system/ResultEnvelopeShell.tsx
sed -n '1,260p' frontend/src/components/ResultEnvelope.module.css
sed -n '1,260p' frontend/src/components/NoResultDisplay.module.css
sed -n '1,260p' frontend/src/design-system/ResultEnvelopeShell.module.css
sed -n '1,260p' frontend/src/api/types.ts
sed -n '440,540p' frontend/src/test/frontendCopyQaHarness.tsx
rg -n "Result headings|Applied filters|No-result guidance|Hero:|Shape/pattern|Backend:" outputs/frontend_copy_qa/20260517T071053Z/frontend_copy_report.md | head -n 80
sed -n '1,260p' frontend/src/components/QueryHistory.tsx
sed -n '1,220p' frontend/src/components/FreshnessStatus.tsx
sed -n '1,240p' frontend/src/components/AppShell.tsx
sed -n '1,220p' frontend/src/components/SampleQueries.tsx
sed -n '220,520p' frontend/src/components/SampleQueries.tsx
sed -n '1,220p' frontend/src/components/SavedQueries.tsx
sed -n '1,220p' frontend/src/components/EmptyState.tsx
git diff --check
rg -n "[^ -~]" return_packages/raw-product/FRONT_FACING_RESULT_UI_PRODUCTIZATION_PREFLIGHT_RETURN_PACKAGE.md
```

Validation result:

- `git diff --check`: PASS.
- ASCII/non-ASCII scan of the return package: PASS, no matches.
- Production code changed: no.
- Frontend rendering changed: no.
- Backend query behavior changed: no.
- Parser behavior changed: no.
- Result contracts changed: no.
- QA corpus changed: no.
- Code tests run: none; this was a preflight documentation/design package.
