# Front-Facing Result UI Productization Wave 1 Return Package

## 1. Executive summary

- What changed: added a frontend display mode model, made `/` public by
  default, moved debug metadata/JSON/actions into Details, and kept debug-rich
  rendering for `/review` and `?debug=1`.
- Backend behavior changed? no
- Parser behavior changed? no
- Result contracts changed? no
- Frontend rendering changed? yes
- Public mode: hides route/query-class/status/reason/debug JSON/dev chrome by
  default while keeping answer content, context chips, caveats, Copy Link, Save
  Query, and feedback actions visible.
- Debug/details mode: preserves route, status, reason, query class,
  freshness/current-through, full query, filters, resolved entities, notes,
  caveats, metadata summary, Copy Query, Copy JSON, and Raw JSON.
- Remaining UI work: Wave 2/Wave 3 are still recommended for deeper answer
  hierarchy, mobile polish, and broader no-result/unsupported copy refinement.

## 2. Display modes

| Mode | Surface | Behavior |
|---|---|---|
| public | `/` default, `/visual-qa` result rendering | Answer-first rendering; debug badges, JSON, Dev Tools, route hints, and raw reason strings are hidden by default. |
| debug | `/?debug=1`, `/review`, frontend-copy QA harness | Existing debug-rich route/status/query-class view remains visible; Copy Query/JSON, Raw JSON, and Dev Tools are available. |
| Details | Public and debug result envelopes/no-result cards | Collapsed disclosure with diagnostics, metadata, notes/caveats, copy actions, and Raw JSON. |

## 3. Public UI changes

| Element | Before | After |
|---|---|---|
| Result action title | `Query output` on `/` | Public `/` shows quieter `Result`; debug keeps `Query output`. |
| Route/query-class/status/reason | Visible before the answer | Hidden in public; preserved in Details/debug. |
| Copy Query / Copy JSON / Raw JSON | Visible on default result view | Hidden by default; available in Details and debug mode. |
| Structured Query Dev Tools | Visible on `/` sidebar | Hidden on public `/`; visible with `?debug=1`. |
| Starter-query renderer hints | Visible on public sample cards | Hidden in public; visible in debug mode. |
| Query history route/query-class badges | Visible in public history | Hidden in public; visible in debug mode. |
| API online/version chrome | Visible in public header | Hidden unless API is offline; debug mode still shows status/version. |

## 4. Details/debug preservation

| Debug info | Where available now | Notes |
|---|---|---|
| Route/status/reason/query class | Result Details; `/review`; `?debug=1` | No backend payload changes. |
| Current-through/data freshness | Result Details; debug envelope | Public answer path no longer leads with raw freshness chrome. |
| Full query text | Details, Copy Query, history, feedback payloads | Public query echo is not first-run chrome. |
| Applied filters | Public chips and Details | Details also retains diagnostic metadata context. |
| Resolved entities/opponents | Details | Uses supplied metadata contexts only. |
| Notes/caveats | Caveats visible when material; all notes/caveats in Details/debug | Public nonmaterial notes are no longer primary chrome. |
| Raw metadata summary | Details | Full response remains in Raw JSON. |
| Copy JSON / Raw JSON | Details and debug surfaces | Public default hides both until Details opens. |

## 5. No-result/unsupported UX

- Public behavior: no-result cards lead with plain product-facing copy and keep
  Submit for review visible.
- Details behavior: raw status, reason, route, query class, unsupported
  filters, notes, caveats, and query text are available behind Details.
- Feedback behavior: no-result and unsupported feedback actions still submit
  the hidden diagnostic context.

## 6. Feedback preservation

- Successful answer reports: still include route, status, reason, result shape,
  metadata, query class, confidence, intent, current-through, notes, caveats,
  and answer preview.
- No-result reports: still include status/reason, metadata, unsupported
  filters, query class, notes, and caveats.
- Hidden metadata preserved? yes

## 7. Tests/validation

- Targeted frontend tests: `npm test -- src/test/useUrlState.test.ts src/test/UIComponents.test.tsx src/test/FirstRun.test.tsx src/test/SavedQueries.test.tsx src/test/LayoutPrimitives.test.tsx src/test/QueryFeedback.test.tsx src/test/ReviewPage.test.tsx src/test/VisualQaPage.test.tsx` passed, 145 tests.
- Frontend-copy QA: `npm run qa:frontend-copy` passed, 125/125 rendered, soft checks `480/0/0`.
- Build: `npm run build` passed with the existing Vite large-chunk warning.
- Lint: `npm run lint` passed with 0 errors and the existing `ReviewPage.tsx` hook warning.
- `git diff --check`: passed.

## 8. Files changed

| File | Change type | Why |
|---|---|---|
| `frontend/src/displayMode.ts` | added | Shared public/debug mode model. |
| `frontend/src/App.tsx` | updated | Derives public/debug mode, hides public debug chrome, reorders public results answer-first. |
| `frontend/src/hooks/useUrlState.ts` | updated | Preserves `?debug=1` across query URL updates. |
| `frontend/src/components/ResultEnvelope.tsx` | updated | Adds public hiding and Details diagnostics drawer. |
| `frontend/src/components/NoResultDisplay.tsx` | updated | Adds public no-result diagnostics disclosure. |
| `frontend/src/components/RawJsonToggle.tsx` | updated | Adds inline mode for Details. |
| `frontend/src/components/SampleQueries.tsx` | updated | Hides renderer hints in public mode. |
| `frontend/src/components/QueryHistory.tsx` | updated | Hides route/query-class badges in public mode. |
| `frontend/src/components/results/ResultRenderer.tsx` | updated | Normalizes display mode and passes it to no-result/renderers. |
| `frontend/src/ReviewPage.tsx` | updated | Forces debug result rendering. |
| `frontend/src/VisualQaPage.tsx` | updated | Uses public result rendering while keeping internal case metadata. |
| `frontend/src/test/*` | updated | Covers public/debug behavior, no-result copy, review/debug preservation, and feedback diagnostics. |
| `docs/operations/ui_guide.md` | updated | Documents public/debug mode and Details behavior. |
| `docs/planning/raw-product/*release*` | updated | Records Wave 1 impact and remaining UI waves. |

## 9. Release impact

- Engine readiness: unchanged; no backend/parser/result-contract changes.
- UI readiness: improved for public default use, with debug diagnostics
  preserved.
- Public launch recommendation: Wave 1 partially addresses the launch UI gap;
  Wave 2/Wave 3 polish is still recommended before broad public launch.
- Next UI wave: tighten answer hierarchy and mobile density, then expand
  no-result/unsupported public copy coverage.
