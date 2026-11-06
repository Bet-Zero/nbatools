# Review of the obsolete ranked-opponent refusal

Reviewer: `/root/team_threshold_checker`, the same separate Codex checker session
as `independent-review.md`. Runtime inspected and executed:
`3105fee4dabfe8826d10151cbe932699800b2af9`. No application change was needed.

**Approve positive support**, replacing only the former refusal assertion for
`LeBron James most points in a game with 5 threes allowed`. The shared opponent
span reader preserves `opponent_fg3m >= 5`, while `pts` remains the player's own
ranking metric. This is whole-game opponent team box-score context. It does not
establish personal defensive assignments, on-court overlap or shots personally
conceded by the player. The applied output filter explicitly identifies OPP FG3M.

Independent arithmetic reads the committed synthetic player/team CSVs directly,
joining `game_id` plus the player's `opponent_team_id` to the other team's
`fg3m`. It filters that opponent value first, then sorts player points descending
and game date descending before the existing five-row display limit.

| Independent query | Qualifying games | Displayed game IDs, in rank order | Player points | Opponent threes |
| --- | --- | --- | --- | --- |
| LeBron, 5 threes allowed | 57 | 425, 376, 453, 416, 531 | 36, 35, 33, 33, 32 | 5, 8, 5, 12, 11 |
| Curry, 18 threes allowed | 11 | 517, 432, 489, 367, 368 | 39, 31, 30, 27, 26 | 24, 18, 22, 20, 18 |

Curry has **zero** own 18-three games in this fixture, and his unrestricted top
five differ, so the second entity/threshold independently discriminates both the
owner and the sample. The engine matches both raw oracles, preserves exactly the
opponent condition, ranks by own points and exposes the opponent label. This is
fixture evidence, not qualification of real NBA values.

The focused independent replay passed **2 selected / 2 executed / 2 passed /
0 skips/failures/errors/xfails**, in 1.57 seconds. The raw oracle, full qualified IDs,
source hashes and replay test are retained beside this receipt. These two checks
are additional to the earlier nineteen; their totals are not an expanded Core-1
acceptance denominator.

The broad execution on `3e38cbe209c2d0d4fa0e972a31b12596d960aeda` remains honestly
**10201 passed / 1863 unavailable-data skips / 2 failed**. One failure is the
stale 600-versus-603 generated Raw QA inventory, separately repaired. The other
was the now-obsolete refusal assertion examined here. Neither historical failure
is erased or called passed. A replacement raw positive test must actually pass,
with the other genuine safety cases unchanged, before integration; final-head CI
and required hosted validation remain separate gates. No source, production,
security, positive-acceptance or publication requirement is relaxed by this
promotion. Repeating the entire unchanged broad suite is not necessary solely
for a test-only positive promotion once these affected reruns and final gates pass.
