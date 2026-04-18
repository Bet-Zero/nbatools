# Phase A Gap Inventory

> **Role:** Reconnaissance artifact produced by Phase A work queue item 2. Classifies every pair in [`parser/examples.md §3`](../architecture/parser/examples.md#3-paired-examples-question-form-vs-search-form) as passing, divergent, or error, and groups the failures by root cause so items 3–8 can consume this as a punchlist.
>
> **How to read:** A pair is "divergent" when both sides parse without error but produce canonically different parse states (excluding `normalized_query`, `confidence`, `alternates`, `intent`). A pair is "error" when at least one side raises. The root-cause categories at the bottom map divergences/errors to the Phase A item that should fix them.
>
> **Snapshot date:** 2026-04-18 (commit preceding queue item 2).

---

## 1. Summary

| Metric    | Count | Notes                                                                          |
| --------- | ----- | ------------------------------------------------------------------------------ |
| Total     | 50    | One pair per row in [`parser/examples.md §3`](../architecture/parser/examples.md#3-paired-examples-question-form-vs-search-form) |
| Pass      | 16    | Question + search form produce identical canonical parse state                 |
| Divergent | 18    | Both sides parse, but canonical parse states differ                            |
| Error     | 16    | At least one side raises `ValueError` (unsupported pattern)                    |

### By section

| Section                             | Pass | Divergent | Error | Phase-scope notes                                       |
| ----------------------------------- | ---: | --------: | ----: | ------------------------------------------------------- |
| §3.1 Leaders and rankings           |    4 |         0 |     1 | Item 3 (leaderboard parity)                             |
| §3.2 Recent / lately / past month   |    2 |         1 |     2 | Items 3 + 9 (fuzzy time)                                |
| §3.3 Last N games / since date      |    3 |         0 |     2 | Items 3, 4                                              |
| §3.4 Best games / biggest games     |    2 |         0 |     3 | Item 3 + product-policy work on "best games"            |
| §3.5 Against good teams             |    2 |         2 |     1 | **Phase E** (opponent-quality); item 3 for the rest     |
| §3.6 When a teammate didn't play    |    1 |         4 |     0 | Items 4 (summary parity), 10 (absence expansion)        |
| §3.7 Who's been the best at __ over |    0 |         0 |     5 | Mixed: items 3 + 9; some "skill filters" are **Phase E** |
| §3.8 Frequency / how often          |    0 |         5 |     0 | Item 6 (occurrence parity)                              |
| §3.9 Record when ___                |    1 |         4 |     0 | Item 5 (record parity)                                  |
| §3.10 Splits / context              |    1 |         2 |     2 | Item 8 (split parity) + context-filter work (**Phase E**) |

---

## 2. Passing pairs (16)

These already route identically and serve as regression guards; item 11's
word-order suite should incorporate them.

| #   | Section | Route                     | Question form                                                  | Search form                          |
| --- | ------- | ------------------------- | -------------------------------------------------------------- | ------------------------------------ |
| 2   | §3.1    | `season_leaders`          | Which players have the most rebounds this year?                | most rebounds this year              |
| 3   | §3.1    | `season_leaders`          | Who has the highest true shooting percentage this season?      | best true shooting percentage this season |
| 4   | §3.1    | `season_team_leaders`     | Which team has the best offensive rating this year?            | best offensive rating team this year |
| 5   | §3.1    | `season_leaders`          | Who has the most assists over the last 10 games?               | most assists last 10 games           |
| 6   | §3.2    | `season_leaders`          | Who scored the most points last night?                         | most points last night               |
| 9   | §3.2    | `season_team_leaders`     | What team has played the best defense recently?                | best defense recently                |
| 11  | §3.3    | `season_leaders`          | Who is averaging the most points in his last 5 games?          | most points last 5 games             |
| 12  | §3.3    | `season_team_leaders`     | Which team has the best net rating in its last 15 games?       | best net rating last 15 games        |
| 13  | §3.3    | `season_leaders`          | Who has made the most threes since January 1?                  | most threes since January 1          |
| 17  | §3.4    | `season_leaders`          | Which players have had the most efficient 30-point games this year? | most efficient 30 point games this year |
| 18  | §3.4    | `season_leaders`          | What are the best rebounding games by centers this season?     | best rebounding games by centers     |
| 22  | §3.5    | `team_record_leaderboard` | What team has the best record against contenders this year?    | best record vs contenders            |
| 25  | §3.5    | `team_record`             | What is the Celtics' record against teams above .600?          | Celtics record vs teams above .600   |
| 27  | §3.6    | `player_game_summary`     | What is the Bucks' record when Giannis Antetokounmpo was out?  | Bucks record when Giannis out        |
| 43  | §3.9    | `player_game_summary`     | What is Denver's record when Nikola Jokić has a triple-double? | Denver record when Jokic triple double |
| 50  | §3.10   | `player_game_finder`      | What is the Nuggets' net rating with Nikola Jokić on the floor versus off the floor? | Nuggets net rating Jokic on off |

Note: pairs #25 and #22 "pass" under the §3.5 opponent-quality label despite the filter not being shipped — both sides currently ignore the "vs contenders" / "vs teams above .600" fragment consistently, which is why they match. Once Phase E ships opponent-quality, these pairs will shift (consistently) to using the filter.

---

## 3. Divergent pairs (18)

Both sides parse without error, but canonical parse states differ. Each row
names the diverging slots and the most likely root cause.

### 3.1 §3.2 — Recent / lately

**#10 `Who has the most double-doubles lately?` vs `most double doubles lately`**
- Route: `player_occurrence_leaders` (both)
- Diverging slots: `leaderboard_intent` (Q=True, S=False); `season` (Q='2025-26', S=None)
- **Cause:** `leaderboard_intent` isn't set on the search form; `lately` resolves to explicit season on the question form but not the search form.
- **Fix item:** 3 (leaderboard signal) + 9 (fuzzy time normalization).

### 3.2 §3.5 — Against good teams

**#21 `Who scores the most against teams over .500 this season?` vs `most points vs teams over .500`**
- Route: `season_team_leaders` (both)
- Diverging slots: `leaderboard_intent` (Q=False, S=True); `stat` (Q=None, S='pts')
- **Cause:** Question form fails to extract stat; search form succeeds. Also `leaderboard_intent` asymmetric.
- **Fix item:** 3 (leaderboard parity), opponent-quality layer deferred to **Phase E**.

**#24 `How has Jayson Tatum played against winning teams this season?` vs `Tatum vs winning teams this season`**
- Route: `player_game_summary` (Q) vs `player_game_finder` (S)
- Diverging slots: `route`, `route_kwargs`, `summary_intent`, `notes`
- **Cause:** Question form's "How has X played" triggers `summary_intent`; search form without that verb phrase falls through to `player_game_finder`.
- **Fix item:** 4 (summary parity — ensure player + timeframe shorthand routes to summary by default).

### 3.3 §3.6 — Teammate absence

**#26 `How do the Suns perform when Devin Booker didn't play?` vs `Suns when Booker out`**
- Route: `player_game_summary` (Q) vs `player_game_finder` (S)
- Diverging slots: `route`, `route_kwargs`, `summary_intent`, `notes`
- **Cause:** Same as #24 — "How do X perform" = summary intent; shorthand without verb falls to finder.
- **Fix item:** 4 + 10 (shorthand `<team> when <player> out` should still route to summary/record).

**#28 `How has Anthony Davis rebounded when LeBron James didn't play?` vs `Anthony Davis rebounds when LeBron out`**
- Route: `player_game_summary` (Q) vs `player_game_finder` (S)
- Diverging slots: same as #26.
- **Fix item:** 4 + 10.

**#29 `What is the Mavericks' offensive rating when Luka Dončić didn't play?` vs `Mavericks offensive rating without Luka`**
- Route: `player_game_finder` (Q) vs `game_finder` (S)
- Diverging slots: `player`, `route`, `route_kwargs`, `without_player`
- **Cause:** On the question form, `detect_without_player` sets `without_player='Luka Dončić'` AND keeps `player='Luka Dončić'` (causing `player_game_finder`). On the search form (`without Luka`), the subject-clear branch fires and routes to `game_finder`. The question form is missing the subject-clear step.
- **Fix item:** 10 (absence phrasing expansion) — generalize subject-clearing to the `when X didn't play` phrasing, not just `without X`.

**#30 `How has Tyrese Maxey played when Joel Embiid was out this season?` vs `Maxey when Embiid out this season`**
- Route: `player_game_summary` (Q) vs `player_game_finder` (S)
- Diverging slots: `route`, `route_kwargs`, `summary_intent`, `notes`, `team`
- **Cause:** Same summary/finder split as #26; additionally question form sets `team='WAS'` (Washington) — likely a false positive on "Wash" / similar? Search form does not. Potential unrelated entity-resolution bug.
- **Fix item:** 4 + 10; note the rogue team resolution for a follow-up.

### 3.4 §3.8 — Frequency / how often

**#36 `How often has Nikola Jokić recorded a triple-double this season?` vs `Jokic triple doubles this season`**
- Route: `player_game_summary` (Q) vs `player_game_finder` (S)
- Diverging slots: `route`, `route_kwargs`, `summary_intent`, `notes`
- **Cause:** "How often" on question form doesn't reliably set `count_intent`; it falls to summary. Search form routes to occurrence-finder. Both are arguably wrong — the target is an occurrence count.
- **Fix item:** 6 (occurrence parity) — ensure `how often` + triple-double phrasing routes through occurrence.

**#37 `How often has Stephen Curry made 5 or more threes this year?` vs `Curry 5+ threes this year`**
- Route: `player_game_finder` (both)
- Diverging slots: `min_value`, `route_kwargs` (presumably the threshold encoding)
- **Cause:** Question form fails to extract `min_value=5`; search form succeeds. Operator alias `"5 or more"` not mapping to threshold.
- **Fix item:** 6 (occurrence parity) + possibly operator normalization per [`specification.md §7.1`](../architecture/parser/specification.md#71-operator-normalization).

**#38 `How often has Luka Dončić scored 40 or more this season?` vs `Luka 40+ point games this season`**
- Route: `player_game_finder` (both)
- Diverging slots: `min_value`, `occurrence_event`, `route_kwargs`, `stat`
- **Cause:** Question form misses stat and threshold; search form picks both up. "40 or more" needs threshold-operator normalization; question form also needs to infer stat from "scored".
- **Fix item:** 6.

**#39 `How often have the Lakers held opponents under 100 points this year?` vs `Lakers opponents under 100 this year`**
- Route: `game_finder` (both)
- Diverging slots: `max_value`, `route_kwargs`, `stat`, `threshold_conditions`
- **Cause:** Question form encodes "under 100 points" as a threshold; search form does not detect "opponents under 100" as a threshold at all.
- **Fix item:** 6 (or a small fix to `_parse_helpers` threshold detection on shorthand).

**#40 `How often has Victor Wembanyama had 5 or more blocks this season?` vs `Wembanyama 5+ blocks this season`**
- Route: `player_game_finder` (both)
- Diverging slots: `min_value`, `route_kwargs`
- **Cause:** Same as #37 — "5 or more" operator alias.
- **Fix item:** 6.

### 3.5 §3.9 — Record when ___

**#41 `What's the Mavericks' record when Luka Dončić scores 35 or more?` vs `Mavericks record when Luka scores 35+`**
- Route: `player_game_summary` (both)
- Diverging slots: `min_value`, `route_kwargs`
- **Cause:** Question form loses the `35` threshold (again an operator-alias issue); search form keeps it.
- **Fix item:** 5 (record parity) + operator normalization.

**#42 `What is the Knicks' record when they allow fewer than 110 points?` vs `Knicks record when allowing under 110`**
- Route: `team_record` (both)
- Diverging slots: `min_value`, `route_kwargs`, `stat`
- **Cause:** Question form sets `min_value=110` and `stat='pts'`; search form extracts neither. Divergent interpretation of "fewer than".
- **Fix item:** 5.

**#44 `What is the Warriors' record when Stephen Curry makes at least 6 threes?` vs `Warriors record when Curry makes 6+ threes`**
- Route: `player_game_summary` (both)
- Diverging slots: `leaderboard_intent`, `threshold_conditions`
- **Cause:** Question form extracts the threshold; search form drops it.
- **Fix item:** 5.

**#45 `What is the Lakers' record when LeBron James and Anthony Davis both play?` vs `Lakers record when LeBron and AD both play`**
- Route: `player_game_summary` (both)
- Diverging slots: `player`, `route_kwargs`
- **Cause:** Question form resolves `player='Carmelo Anthony'` (wrong — probably catching "Anthony"); search form resolves `player='LeBron James'`. Both are arguably wrong (target is a conjunction, two players). Definitely a regression-prone entity-resolution edge.
- **Fix item:** 5 + the multi-player-AND case is arguably out of scope for Phase A (multi-intent is §8 exclusion in the plan). Flag for retrospective discussion; short-term at least the two forms should agree.

### 3.6 §3.10 — Splits / context

**#47 `Which teams have the best road record this year?` vs `best road record this year`**
- Route: `team_record_leaderboard` (both)
- Diverging slots: `team_leaderboard_intent` (Q=True, S=False)
- **Cause:** Intent flag asymmetry only — routing is stable.
- **Fix item:** 3 or 8 (cosmetic; may not change user-visible behavior but breaks equivalence).

**#48 `How does Anthony Edwards shoot in wins versus losses?` vs `Anthony Edwards shooting in wins vs losses`**
- Route: `player_game_finder` (Q) vs `player_split_summary` (S)
- Diverging slots: `route`, `route_kwargs`, `split_intent`, `split_type`, `notes`
- **Cause:** "How does X shoot in wins versus losses" fails to trigger `split_intent`; the search form does. Question form falls to finder.
- **Fix item:** 8 (split parity).

---

## 4. Error pairs (16)

Pairs where at least one side raises `ValueError` ("Could not map query to a
supported pattern yet"). For each, we note which side(s) fail and the most
likely cause.

### 4.1 Both sides fail — capability genuinely unshipped or unsupported

| #   | Section | Pair                                                                                   | Root cause                                        | Phase        |
| --- | ------- | -------------------------------------------------------------------------------------- | ------------------------------------------------- | ------------ |
| 1   | §3.1    | `Who leads the NBA in points per game...` / `points per game leaders this season`      | "leads the NBA" / "leaders this season" base form not recognized. | 3            |
| 7   | §3.2    | `...hottest from three lately` / `hottest from 3 lately`                               | "hottest from three" as a skill/stat phrasing.    | 3 or 9       |
| 14  | §3.3    | `...averaged a double-double over their last 10 games` / `double double average last 10 games` | "averaged a double-double" pattern.           | 3 or 6       |
| 16  | §3.4    | `biggest scoring games this season` / (same)                                           | "biggest scoring games" — season-high variant     | 3 (product policy on "best games") |
| 19  | §3.4    | `best all-around games` / (same)                                                       | No defined stat for "all-around"; undefined term. | Out (guardrail §7.2) |
| 20  | §3.4    | `highest assist games by point guards` / (same)                                        | Position filter + "highest X games" pattern.      | 3            |
| 23  | §3.5    | `...shoot the best against top-10 defenses` / `best shooting vs top 10 defenses`       | Opponent-quality filter not shipped.              | **Phase E**  |
| 31  | §3.7    | `best rebounder past month`                                                            | Skill-phrasing ("rebounder") + past-month.        | 3 + 9        |
| 32  | §3.7    | `best shot blocker last 10 games`                                                      | Skill-phrasing ("shot blocker").                  | 3            |
| 33  | §3.7    | `best playmaker since the All-Star break`                                              | Skill-phrasing ("playmaker").                     | 3            |
| 34  | §3.7    | `best catch-and-shoot player this season`                                              | "Catch-and-shoot" — undefined skill bucket.       | Out (guardrail §7.2) / **Phase E** |
| 35  | §3.7    | `best transition scorer lately`                                                        | "Transition scorer" — undefined skill bucket.     | Out (guardrail §7.2) / **Phase E** |

### 4.2 Only question form fails (search form parses)

| #   | Section | Question form                                                           | Search form (parses)                        | Root cause                       | Phase |
| --- | ------- | ----------------------------------------------------------------------- | ------------------------------------------- | -------------------------------- | ----- |
| 8   | §3.2    | `Who has been the best scorer over the past month?`                     | `best scorers past month`                   | "best scorer" + "over the past month" phrasing lost. | 3 + 9 |
| 15  | §3.3    | `Who is shooting the best from three over the last month with at least 5 attempts per game?` | `best 3pt percentage last month min 5 attempts` | Long "shooting the best from three" phrasing not mapped to fg3_pct. | 3 |
| 46  | §3.10   | `Who scores the most at home this season?`                              | `most points at home this season`           | "Who scores the most" (no stat) + context filter. | 3 or 8 |
| 49  | §3.10   | `Which players score the most in the 4th quarter this season?`          | `most 4th quarter points this season`       | Quarter context filter ("4th quarter") on question-form player leaderboards. | **Phase E** context filters; leaderboard wording (3) |

---

## 5. Root-cause punchlist for items 3–11

Grouped so later queue items can consume this directly.

### Item 3 — Leaderboard phrasing parity

- **Operator/verb phrases to recognize:** `leads the NBA in X`, `X leaders this season`, `Who scores the most`, `Who has been the best X`, `best X over the last N games / past month`, `best X past month`, `X past month`, `best shot blocker`, `best playmaker`, `best rebounder`, `highest X games by <position>`, `biggest scoring games`.
- **Pairs in scope:** #1, #8 (Q side), #10 (intent flag), #15 (Q side), #20, #21 (stat extraction), #31, #32, #33, #47, plus the already-known #7.1 leaderboard forms (`last 10 scoring leaders`, `top scorers last 10 games`, `highest scorers last 10`) identified in the item 1 commit message.

### Item 4 — Summary phrasing parity

- **Verb-phrase triggers for summary:** `How has X played`, `How does X perform`, `How do the Xs perform`, `How has X rebounded/scored/shot`.
- **Pairs in scope:** #24, #26, #28, #30, the question-form side of the §3.6 items where shorthand drops to finder.
- Ensure the default `<player/team> + <timeframe>` → summary rule fires for both forms.

### Item 5 — Record phrasing parity

- **Threshold operators lost in question form:** `"X or more"`, `"at least X"`, `"fewer than X"`, `"under X"` (on some paths). Operator normalization per [`specification.md §7.1`](../architecture/parser/specification.md#71-operator-normalization) likely the consolidated fix.
- **Pairs in scope:** #41, #42, #44, #45 (multi-player AND is partially out of scope per plan §8).

### Item 6 — Occurrence / frequency phrasing parity

- **Triggers:** `how often`, `how many`, with threshold aliases `"5 or more"`, `"N+"`, `"at least N"`.
- **Pairs in scope:** #36, #37, #38, #39, #40.
- Likely needs `count_intent` detection broadened for `how often` on player + threshold inputs.

### Item 8 — Split and context phrasing parity

- **Triggers:** `How does X shoot in wins versus losses`, `in wins vs losses` (verb-form).
- **Pairs in scope:** #48, partial #47 (intent flag), partial #49.
- Note `at home this season` and `4th quarter` overlap with context-filter work that is Phase E — flag them here but defer.

### Item 9 — Fuzzy time-word expansion

- **Terms to formalize:** `past month`, `lately`, `recently`, `over the past month`, `over the last month`, `since the All-Star break` (already recognized on both sides of #33 error? — verify).
- **Pairs in scope:** #7 (both sides fail on "hottest from three lately"), #8 (Q side), #10 (season divergence), #31 (past month).

### Item 10 — Absence phrasing expansion

- **Triggers in scope:** `when X didn't play` (question form variant of `without X`), `when X was out`.
- **Pairs in scope:** #26, #28, #29 (subject-clear asymmetry), #30.

### Out of scope for Phase A (defer to Phase E or flag for guardrail §7.2)

- **Opponent-quality:** #23 (top-10 defenses), #21 (teams over .500 — parses consistently but semantic coverage is Phase E), #22, #24, #25.
- **Undefined fuzzy-skill buckets without glossary definition:** "all-around games" (#19), "catch-and-shoot" (#34), "transition scorer" (#35). Per guardrail §7.2 these should return "not supported" unless Phase B codifies them in the glossary.
- **Context filters (clutch / quarter):** #49 (4th quarter).
- **Multi-player AND conjunction:** #45 (`LeBron and AD both play`) — plan §8 excludes multi-intent.

---

## 6. Known anomalies discovered (to revisit in retrospective)

- **#30 rogue team resolution** — question form resolves `team='WAS'` for "How has Tyrese Maxey played when Joel Embiid was out". Unrelated to Phase A's surface-form goal but worth flagging for the retrospective / entity-resolution follow-up.
- **#45 `player='Carmelo Anthony'` resolution** — on "LeBron James and Anthony Davis both play", the conjunction confuses the resolver.

---

## 7. Method

- Source data: [`parser/examples.md §3`](../architecture/parser/examples.md#3-paired-examples-question-form-vs-search-form), 50 pairs.
- Script: ran `parse_query(question_form)` and `parse_query(search_form)` for each pair, compared canonical parse state (exclude `normalized_query`, `confidence`, `alternates`, `intent`). The classification script is preserved at [`tests/test_parser_equivalence_groups.py`](../../tests/test_parser_equivalence_groups.py) via the helper introduced in Phase A item 1.
- Snapshot committed with Phase A item 2. Re-run after each subsequent item to track progress.
