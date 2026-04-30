# Phase P2 State Inventory

> **Role:** Runtime-state inventory for
> [`phase_p2_work_queue.md`](./phase_p2_work_queue.md). This records the
> loading, empty, no-result, error, retry, and freshness states that Phase P2
> will polish before changing runtime behavior.

---

## Boundary

P2 owns states that appear when the app is not rendering a successful result
section, or when result trust/recovery needs explicit UI support:

- request loading
- API no-result responses
- API unsupported and ambiguous responses
- API error responses delivered inside the normal `QueryResponse` envelope
- client-side/API/network failures that prevent a `QueryResponse`
- stale, unknown, or failed freshness status
- technically successful responses whose result sections are empty

React remains a presentation layer. P2 may choose state-specific copy,
suggestions, disclosure, and retry controls from supplied API/client state, but
it must not parse the query or invent data.

---

## Current Ownership

| State | Current owner | Current behavior | P2 affordance decision |
| ----- | ------------- | ---------------- | ---------------------- |
| First-run/no-query | `App.tsx` chooses `EmptyState` when not loading, no result, and no error | P1 first-run surface with grouped starter queries and freshness banner | Preserve as a regression boundary, not a P2 redesign target. |
| Loading request pending | `App.tsx` `loading` state renders `Loading.tsx` | Card with status role, spinner, "Searching NBA data..." copy, `SkeletonText`, and `SkeletonBlock` preview | P2 item 2 should refine this into a compact result-preview skeleton, preserve `role="status"`/`aria-live`, and avoid facts before the API responds. No retry while pending. |
| API no result: `no_match` | `ResultSections.tsx` routes empty or missing sections with `result_status="no_result"` to `NoResultDisplay.tsx` | "No Results" copy, generic suggestions, notes when supplied | P2 item 3 should keep suggestions because the user can recover by editing spelling/scope/filters. Notes remain visible. |
| API no result: `no_data` | `NoResultDisplay.tsx` via `ResultSections.tsx` | No-results variant with data-unavailable message and generic suggestions | P2 item 3 should keep recovery guidance conservative: edit season/scope where useful, show notes/details, and avoid implying missing data exists. |
| API no result: `unrouted` | `NoResultDisplay.tsx` via `ResultSections.tsx` | Message says the query type is not yet supported; suggestions currently show because only `unsupported` and `ambiguous` suppress them | P2 item 3 should treat this like an unsupported product boundary unless API alternates are supplied. Do not add parser-side suggestions in React. |
| API unsupported: `unsupported` | `NoResultDisplay.tsx` via `ResultSections.tsx` | "Unsupported Query" variant, warning badge, supplied notes, no suggestions | P2 item 3 should keep this distinct from no-match. Show supplied notes/caveats and do not show generic suggestions unless the API supplies alternates. |
| API ambiguous: `ambiguous` | `NoResultDisplay.tsx` via `ResultSections.tsx` | "Ambiguous Query" variant, warning badge, supplied notes, no suggestions | P2 item 3 should explain specificity, preserve notes, and avoid client-side entity disambiguation logic. API alternates remain the only source for alternate buttons. |
| API error envelope: `result_status="error"` | `ResultSections.tsx` routes empty/missing sections to `NoResultDisplay.tsx`; `ResultEnvelope.tsx` still shows envelope metadata | "Query Error" variant with notes; distinct from thrown network/client errors | P2 item 3 can polish this as a result-level error. It should not show a network retry unless the request itself failed. |
| Client/network failure: natural query | `App.tsx` catches `postQuery` rejection and renders `ErrorBox.tsx` | Raw error message under a simple "Error" label; result cleared; no retry | P2 item 4 should add safe copy and a retry action that calls the existing natural-query handler for the last attempted query and preserves URL/history behavior. |
| Client/network failure: structured query | `App.tsx` catches `postStructuredQuery` rejection and renders `ErrorBox.tsx`; `DevTools` can also call `onError` | Raw error message; no retry; invalid URL kwargs show "Invalid kwargs in URL" | P2 item 4 should support retry for the last attempted route/kwargs through the existing structured handler. Invalid kwargs should remain a validation error, not a retryable network error. |
| API offline chrome | `App.tsx` `fetchHealth` failure sets `apiOnline=false`; header shows "API offline"; freshness panel is hidden | Shell-level status only | P2 item 4 should keep this distinct from query no-result states. Offline copy can support the failure state, but no response data should be fabricated. |
| Freshness stale/unknown/failed | `FreshnessStatus.tsx`, mounted by `AppShell` through `App.tsx` | Panel or first-run banner shows `fresh`, `stale`, `unknown`, or `failed`; details expand to season/refresh information | Preserve component ownership. P2 can ensure failure/error-state copy does not conflict with freshness trust messaging. Retry is out of scope unless a refresh endpoint exists. |
| Successful response with empty sections | `ResultSections.tsx` returns `null` for `result_status="ok"` when sections are absent or every section array is empty | Result envelope and raw JSON still render, but the result-section area has no designed empty body | Capture as a residual for P2 item 3. If the API says `ok`, React should not convert it to no-result, but it may show a neutral "No displayable rows" state when sections are structurally empty. |

---

## Fixture Matrix

| Fixture | Owner test file | Data shape | Purpose |
| ------- | --------------- | ---------- | ------- |
| Loading skeleton | `frontend/src/test/UIComponents.test.tsx`; future app-level test can keep `postQuery` pending | Render `<Loading />`, or submit a query while the mocked request promise is unresolved | Verify status semantics, loading copy, skeleton labels/structure, and mobile containment. |
| No-match response | `frontend/src/test/UIComponents.test.tsx`; `ResultSections.test.tsx` for envelope routing | `result_status: "no_result"`, `result_reason: "no_match"`, no result sections or empty sections | Verify recoverable no-result copy, suggestions, and notes. |
| No-data response | `UIComponents.test.tsx` | `result_status: "no_result"`, `result_reason: "no_data"`, optional notes | Verify data-unavailable copy that does not promise data exists. |
| Unrouted response | `UIComponents.test.tsx` or `ResultSections.test.tsx` | `result_status: "no_result"`, `result_reason: "unrouted"` | Verify unsupported-query treatment and no client parser logic. |
| Unsupported response | `UIComponents.test.tsx` | `result_status: "no_result"`, `result_reason: "unsupported"`, notes such as invalid filter combinations | Verify distinct unsupported layout, no generic suggestions, and visible notes. |
| Ambiguous response | `UIComponents.test.tsx` | `result_status: "no_result"`, `result_reason: "ambiguous"`, notes naming possible matches when supplied | Verify specificity guidance without client-side disambiguation. |
| API error envelope | `UIComponents.test.tsx` and `ResultSections.test.tsx` | `result_status: "error"`, `result_reason: "error"`, empty or missing sections, safe notes | Verify result-level error treatment separate from transport failure. |
| Natural-query network failure | Future focused app test, likely `frontend/src/test/FirstRun.test.tsx` or a dedicated app state test | Mock `postQuery` rejection with `new Error("Network request failed")` after submitting text | Verify safe error copy and retry calls the existing natural-query path. |
| Structured-query network failure | Future focused app/dev-tools test | Mock `postStructuredQuery` rejection for `{ route, kwargs }` | Verify retry calls the existing structured-query path and preserves URL state. |
| Invalid structured kwargs | Existing URL/dev-tools path, future app test if touched | URL has `route` plus invalid `kwargs` JSON | Verify validation message remains non-retryable and safe. |
| API offline header | Future app-level test if item 4 touches shell status | Mock `fetchHealth` rejection | Verify offline shell status remains separate from query result state. |
| Freshness stale | `frontend/src/test/FreshnessStatus.test.tsx` | Freshness response `status: "stale"`, old `current_through` | Verify stale trust copy and expandable details. |
| Freshness unknown | `FreshnessStatus.test.tsx` | Freshness response `status: "unknown"`, `current_through: null` | Verify unknown trust copy. |
| Freshness failed | `FreshnessStatus.test.tsx` | Freshness response `status: "failed"`, `last_refresh_ok: false`, `last_refresh_error` | Verify failed trust copy and safe detail disclosure. |
| Empty ok sections | Existing `frontend/src/test/ResultSections.test.tsx` covers empty ok leaderboard sections | `result_status: "ok"`, non-null `sections` object with every section array empty | Decide whether P2 item 3 adds a neutral section-empty display while keeping `ok` semantics intact. |

---

## Copy And Recovery Decisions

- Loading copy should say the app is searching/running, not what it will find.
  Skeletons may suggest result shape, but not specific players, teams, stats,
  or counts.
- No-match and no-data states may show general editing suggestions because the
  request completed and the user can recover by changing spelling, scope, date,
  or filters.
- Unsupported, unrouted, and ambiguous states should not show generic
  suggestions by default. They should show supplied API notes and API-supplied
  alternates when present.
- API error envelopes are result states. They should preserve the envelope and
  notes, and should not be conflated with network failures.
- Client/network failures are transport states. They need a retry affordance,
  safe human copy, and no stack traces or implementation internals.
- Freshness states are trust states, not query errors. Stale/unknown/failed
  data should remain visible in shell chrome and should not be hidden by a query
  failure card.
- Empty `ok` sections are an API/display mismatch, not proof of a no-result
  query. A neutral empty-section state is acceptable if it preserves the `ok`
  status and envelope.

---

## Residuals For Runtime Items

- Item 2 should preserve loading accessibility while improving the skeleton
  hierarchy. No unresolved design decision blocks it.
- Item 3 should decide the exact empty-`ok` treatment. The conservative
  implementation is a neutral "No displayable rows" state in the result-section
  area, not a `no_result` conversion.
- Item 4 needs to remember the last attempted natural or structured request in
  `App.tsx` so retry can reuse existing handlers. This is implementation work,
  not a blocker.
- No P2 state requires React-side query parsing, entity resolution, or data
  transformation.
- Browser screenshot verification remains part of later mobile/felt-polish
  work unless a P2 runtime change creates an obvious responsive risk.
