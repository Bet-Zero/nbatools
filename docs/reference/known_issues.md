# Known Issues (Backlog)

Small, non-urgent engineering findings from the July 2026 full-system review
that were never scheduled or fixed. None of these block anything or affect
release status — they are ordinary backlog, independent of the
[2026-08-02 Queue E scope decision](../audits/2026-08-02-queue-e-scope-decision/README.md).
Fuller technical detail for each (severity, original discovery context) is
in the review's archived closure report, kept locally and not tracked in
git; this doc is the durable, plain-language record going forward.

## Saved structured-query safety (FSR-024)

**Where:** `frontend/src/storage/savedQueryStorage.ts`

**What it means:** When a user saves a structured search (not a typed
question, but one built from filters) and reloads it later, the code
doesn't carefully validate what it's loading before rerunning it. A
malformed or outdated saved entry can silently rerun as if it were typed
natural-language text instead of replaying the exact saved filters — so a
reloaded saved search isn't guaranteed to match what was originally saved.

**Fix shape:** Add versioned validation/migration for saved entries, quarantine
anything malformed instead of guessing, and rerun saved items using their
exact stored route and filters (or drop the "saved structured query" claim
if that's not worth building).

**Priority:** Low — a reliability nice-to-have, not a live bug affecting any
current answer.

## Frontend depends on backend wording (FSR-025)

**Where:** likely `frontend/src/components/NoResultDisplay.tsx` and
`frontend/src/components/noResultDisplayUtils.ts` (the "can't answer that
one yet" / guidance-card logic); needs re-confirming against current code
before a fix.

**What it means:** Part of the website's display logic decides what to show
by inspecting the literal wording of a backend message, instead of the
backend sending a stable code (like `unsupported_boundary`) that means the
same thing regardless of phrasing. Risk: rewording a backend message for an
unrelated reason (a copy fix, a typo) could silently break frontend behavior
that was quietly parsing the old wording.

**Fix shape:** Add stable notice/guidance codes to the shared result
contract; migrate the frontend to read codes instead of text, with a safe
fallback for unrecognized codes.

**Priority:** Low/medium — a maintainability landmine for future edits, not
a bug affecting users today.

## Browser asset caching (FSR-030)

**Where:** `api/assets.py` and `src/nbatools/vercel_functions.py`
(`ui_asset_response`) — no `Cache-Control` header is currently set for
built JS/CSS assets.

**What it means:** The website's fingerprinted JS/CSS files (filenames that
change whenever the content changes, e.g. `index-Bl6BAKFx.js`) are supposed
to be safe for browsers to cache indefinitely, since a new version always
gets a new filename. Right now the server doesn't tell browsers that, so
every page load re-downloads assets that could have been cached. Pure
performance/bandwidth, not correctness or security.

**Fix shape:** Set a long-lived immutable `Cache-Control` header for
fingerprinted asset responses; keep HTML non-cached/revalidated as-is.

**Priority:** Low now; would become worth doing if real traffic increases.
