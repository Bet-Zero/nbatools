# Correctness Fixes Pass 3 Report

This pass fixes five correctness issues from the pass-2 `/review` screenshot review: missing count answers for game-finder routes, incomplete game-summary answers, opponent-points parser ambiguity, unknown playoff-round display, and team-subject verb agreement.

## Issue 1 - Game Finder Count Headlines

Files touched:

- `src/nbatools/commands/_parse_helpers.py`
- `src/nbatools/commands/_occurrence_route_utils.py`
- `src/nbatools/commands/natural_query.py`
- `src/nbatools/commands/player_game_finder.py`
- `src/nbatools/query_service.py`
- `frontend/src/components/results/patterns/GameLogResult.tsx`
- `tests/test_explicit_intent_queries.py`
- `tests/test_parser_equivalence_groups.py`
- `tests/test_query_service.py`

`count_phrase` population was extended in `src/nbatools/query_service.py` through `_build_count_phrase`, with count intent recognition widened in `_parse_helpers.wants_count` to include `how often`. Natural-query routing now keeps how-often player event queries on `player_game_finder` while still passing `special_event` through `natural_query.py` and `player_game_finder.py`, so finder results can return a primary count sentence instead of only stat boxes.

Verified local examples:

- `How often has Nikola Jokić recorded a triple-double this season?` returns `player_game_finder` with `Nikola Jokić has recorded 34 triple-doubles this season.`
- `How often have the Lakers held opponents under 100 points this year?` returns `game_finder` with `The Lakers have held opponents under 100 points 7 times this season, going 7-0.`

The local dataset differs from the screenshot counts: the corrected Lakers opponent-under-100 sample is 7 games and 7-0 locally, not the previous 8 losses that came from filtering Lakers own points.

## Issue 2 - Game Summary Log Shape

Files touched:

- `src/nbatools/commands/game_summary.py`
- `src/nbatools/query_service.py`
- `frontend/src/api/types.ts`
- `frontend/src/components/results/config/routeToPattern.ts`
- `frontend/src/components/results/patterns/GameLogResult.tsx`
- `frontend/src/test/ResultRenderer.test.tsx`
- `tests/test_query_service.py`

`game_summary` now returns a filtered `game_log` section for absence queries, and `query_service` adds `answer_phrase`, `record_wins`, `record_losses`, `record`, and `primary_count` metadata. The game-log renderer uses `answer_phrase` above the stat strip for summary-only shapes and no longer renders the malformed fallback table or empty `GAME DETAIL`, `SUMMARY DETAIL`, and `BY SEASON DETAIL` drawers for this route.

Verified local example:

- `How do the Suns perform when Devin Booker didn't play?` returns `The Suns are 8-10 in 18 games without Devin Booker, averaging 103.8 PPG.`

## Issue 3 - Opponent Points Parser

Files touched:

- `src/nbatools/commands/_parse_helpers.py`
- `src/nbatools/commands/natural_query.py`
- `src/nbatools/commands/game_finder.py`
- `src/nbatools/commands/game_summary.py`
- `src/nbatools/query_service.py`
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/components/results/patterns/GameLogResult.tsx`
- `frontend/src/test/LayoutPrimitives.test.tsx`
- `tests/test_explicit_intent_queries.py`

Supported opponent-points phrasings now include:

- `held opponents under N points`
- `held them to under N points`
- `limited opponents to under N points`
- `kept the other team below N points`
- `allowed under N points`
- `gave up fewer than N points`
- shorthand `opponents under N`

The parser produces an `opponent_pts` threshold instead of a subject `pts` threshold for these forms. The command layer derives `opponent_pts` from existing game-log fields when needed, and the UI chip label renders this axis as `OPP <= 100 PTS`.

Related follow-up surfaced: the screenshot expectation of `8 times` appears to reflect the previous wrong own-points filter. With the local data, the corrected opponent-points filter returns 7 Lakers wins.

## Issue 4 - Unknown Round Display

Files touched:

- `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx`
- `frontend/src/test/ResultRenderer.test.tsx`

`Unknown Round` and unknown/null round values now display as an em dash in playoff history and playoff matchup-history tables. The caveat remains the explanatory source of truth for pre-2001 round coverage.

## Issue 5 - Team Headline Verb Agreement

Files touched:

- `frontend/src/components/results/patterns/PlayoffHistoryResult.tsx`
- `frontend/src/test/ResultRenderer.test.tsx`

Team-subject playoff headlines now use plural sports-team verbs:

- `Lakers have ...`
- `Indiana Pacers own ...`

The same renderer covers playoff-history and round-record headline strings for the reported cases.

## Verification

Automated checks run:

- `PATH=.venv/bin:$PATH make test-query` - passed, 676 tests.
- `npm test` from `frontend/` - passed, 18 test files and 243 tests.
- `npm run build` from `frontend/` - passed and rebuilt `src/nbatools/ui/dist`.
- Targeted failing-test rerun after the stretch-route kwarg fix - passed, 54 tests.
- Focused opponent-points parser phrasing rerun - passed, 8 tests.
- `PATH=.venv/bin:$PATH make test-preflight` - passed, 2,614 tests and 1 xpassed.
- `PATH=.venv/bin:$PATH make test` - passed, 2,653 tests and 1 xpassed.

Targeted `/review` Playwright verification was run against `http://127.0.0.1:8012/review` with the pass-3 fixture set narrowed to the affected cases. It confirmed:

- Jokić triple-double count renders the count headline and no stat-box summary strip.
- Lakers opponent-under-100 count renders the count headline, `OPP <= 100 PTS` chip, 7 rows with `opponent_pts < 100`, and a 7-0 local record.
- Suns without Booker renders the W-L answer sentence, has an 18-row `game_log`, and does not render empty summary/by-season detail placeholders.
- Lakers playoff history uses plural `have` and displays em dash placeholders instead of `Unknown Round`.
- Best finals record uses `Indiana Pacers own 66.7% finals playoff mark`.
