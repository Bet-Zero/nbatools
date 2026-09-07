# Compound event and filter routing

## What this boundary decides

A question can carry several meaningful things at once. When it does, a route
may answer only if it accounts for all of them. If it cannot, the honest reply
is a refusal that names what it could not do — not a smaller answer to a
question nobody asked.

The boundary lives in `src/nbatools/commands/_compound_event_authorization.py`.

## The four things a compound question carries

| Component | What it is | Example |
| --- | --- | --- |
| ranking key | what the rows are ordered by | count of matching games |
| event conditions | what makes one game count | team points ≥ 120, threes ≥ 15 |
| filters | the scope | seasons, dates, teammate availability |
| residual | wording nothing above accounted for | — |

`teams with most games scoring 120+ and making 15+ threes since 2020` means:
rank teams by **how many games matched**, where a game matches when the team
scored 120 *and* made 15 threes, inside a since-2020 window.

Its ranking key is a count. Neither `120` nor `15` is the key — they are
conditions. Reading the last-detected threshold as a ranking metric is what
turned this question into a league three-pointers-per-game leaderboard.

## The invariant

> Before a compound or event-shaped request executes, every meaningful
> component must be **accounted for**: the route executes it, it defines the
> route's semantics, or it is named as unsupported in a refusal that returns no
> answer.

"The parser recognized it" is not on that list. A component the parser read and
no route executed is the defect, not the evidence against it.

### A game-level condition needs a game-level route

The sharpest form of the rule. A season leaderboard's unit of execution is a
whole season, so it cannot apply a *game-level* condition at all. Handing it
"15+ threes" produced a filter on the season **average** — a different question
with an entirely plausible-looking answer.

| Ranking mode | Routes | Ranking key | Executes game-level conditions |
| --- | --- | --- | --- |
| occurrence count | `player_occurrence_leaders`, `team_occurrence_leaders` | count of matching games | yes, all of them |
| season aggregate | `season_leaders`, `season_team_leaders` | one season column | no — except an occurrence-count column |
| single-game ranking | `top_player_games`, `top_team_games` | one game's box-score value | yes |
| game list | `game_finder`, `player_game_finder` | the finder's sort | yes |

An occurrence-count column (`games_30p`, `games_10r`) is the one exception on a
season board: its name *encodes* one event condition, so ranking `games_30p`
genuinely counts 30-point games. "30-point games" and `games_30p` are the same
statement, not two competing metrics.

## Governed routes

Occurrence, single-game-ranking, game-finder and season-leaderboard routes.
Fixed-metric record, playoff-appearance, playoff-round, decade, stretch and
lineup routes are deliberately **not** governed here — whether they drop an
unexecuted extra clause is a separate project.

## The checks, in order

1. **Every stated event condition is executed.** A condition the route never
   received is a piece of the question that silently stopped existing.
2. **No condition metric occupies the ranking-key slot.** On a count route with
   a conditions list, a `stat` kwarg means the route is about to order by a
   threshold instead of counting matches.
3. **No named ranking metric is discarded.** A metric named outside every
   condition is a ranking key the question asked for. `most efficient 30-point
   games` names True Shooting % — the repo's own existing reading of
   "efficient" — and no route ranks individual games by it.
4. **An availability condition is executed or refused.** Whole-game teammate
   presence/absence is execution-backed on a small set of routes; availability
   *status* is backed nowhere, because the product holds no injury data.

## Blocker id

One id, not a taxonomy. What specifically could not run travels in the refusal
metadata rather than in a family of ids. Like every blocker id it is backend and
test vocabulary, never product copy.

| Id | Meaning |
| --- | --- |
| `compound_event_request_unexecutable` | a compound/event-shaped request the selected route cannot execute in full |

## Refusal metadata contract

Nothing ran, so nothing is published as the thing that ran.

| Field | On a compound refusal |
| --- | --- |
| `stat` | null — never a metric, because no ranking and no finder executed |
| `ranking_key` | absent, since no route ranked anything |
| `requested_event_conditions` | every stated condition, whole or not at all |
| `requested_stat` | the ranking metric the route could not order by, when that is why |
| `unsupported_scope` | what this route would have ranked by instead |
| `unsupported_availability` | the availability condition the route cannot apply |
| `applied_filters` | empty — no filter was applied |

`requested_event_conditions` is published whole or not at all, for the same
reason `requested_metrics` is: a one-entry list presented as the request is the
silent reduction this boundary removes.

## `ranking_key` on answers that do run

Successful results on governed routes publish `ranking_key`, so a consumer can
tell "ranked by how many games matched" (`occurrence_count`) from "ranked by
threes made" (`season_aggregate`) without inferring it from a `stat` field. On a
compound occurrence route `stat` is suppressed entirely: any stat there names a
*condition* being counted, and publishing it as the answer's metric is the
promotion this boundary exists to stop.

## What this boundary does not decide

- unexecuted qualifiers on fixed-metric routes (a separate project);
- filter execution receipts (a separate project);
- the meaning of vague words. `depleted`, `shorthanded` and `stayed afloat`
  acquire no meaning here. `efficient` is resolved only because
  `_leaderboard_utils.LEADERBOARD_STAT_ALIASES` already mapped it to `ts_pct`
  before this project and the glossary already documents it as shipped — and
  resolving it still ends in a refusal, because no route ranks single games by
  it;
- injuries. `injured` is *recognized* so the clause can be refused. Nothing here
  decides what counts as injured, and nothing infers it from missed games.

## A note on `was`

`was` is both the Washington abbreviation and the English copula, so
`most 40-point games while the player was injured` resolved a Wizards subject
nobody asked for and answered a Washington question. The verb reading is now
masked before any alias scan (`entity_resolution.mask_copula_team_lookalikes`).
`was record this season` still resolves the Wizards.
