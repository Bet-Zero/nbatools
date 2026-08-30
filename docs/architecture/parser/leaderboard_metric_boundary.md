# Leaderboard metric boundary

## What this boundary decides

A ranking question has to say what to rank by. When it does not, the honest
reply is to ask which stat - not to pick one.

The boundary in `src/nbatools/commands/_leaderboard_eligibility.py` is the
single decision behind every ranking branch that *chooses* its metric from the
query. It guarantees six things for those branches:

1. no ranking metric is invented when none was requested;
2. several requested ranking metrics are not silently reduced to one;
3. an unsupported requested metric or scope is not replaced with another metric;
4. aggregation wording - total, per game, average, rate, combined, cumulative -
   is not silently discarded;
5. a refused request publishes no executed stat;
6. clear existing metric forms keep working.

## What it does not decide

This boundary is **not** universal residual-clause protection. It is scoped to
metric selection and aggregation integrity on variable-metric ranking branches.
It does not cover:

- fixed-metric and record routes, whose metric the route supplies;
- playoff appearance, playoff round-record, occurrence, stretch, lineup and
  decade routes;
- compound threshold and event routing;
- availability conditions on every route;
- vague or narrative language;
- filter execution receipts.

Those are separate, real trust projects. Naming them here keeps the claim this
boundary makes the same size as the thing it actually does.

## Governed route families

| Route family | Metric source | No metric named | Metric scope unsupported |
| --- | --- | --- | --- |
| `season_leaders` (league-wide) | query, via the player leaderboard vocabulary | `leaderboard_metric_required` | `leaderboard_metric_unavailable_for_scope` |
| `season_team_leaders` (league-wide) | query, via the team leaderboard vocabulary | `leaderboard_metric_required` | `leaderboard_metric_unavailable_for_scope` |
| `season_leaders` (rookie population) | query | `leaderboard_metric_required` | `leaderboard_metric_unavailable_for_scope` |
| `season_leaders` (sophomore population) | query | `leaderboard_metric_required` | `leaderboard_metric_unavailable_for_scope` |
| `season_leaders` (starter / bench role) | query | `leaderboard_metric_required` | `leaderboard_metric_unavailable_for_scope` |
| `season_leaders` (team-scoped player leader) | query, via `team_leader_stat` | `leaderboard_metric_required` | `leaderboard_metric_unavailable_for_scope` |
| `top_player_games` (league-wide season high) | query | `leaderboard_metric_required` | `leaderboard_metric_unavailable_for_scope` |
| `top_team_games` (season high, top-team-game intent) | query | `leaderboard_metric_required` | `leaderboard_metric_unavailable_for_scope` |
| metricless ranking that matched no route | query | `leaderboard_metric_required` | n/a |

A population is not a metric. "Rookie leaders" says who to rank, never what to
rank them by, so a specialized population reaches the same decision as any
other ranking.

## Deferred route families

These rank by a metric the route itself supplies, so "which stat?" is not a
question they can be asked. Whether they drop an unsupported extra clause is a
real defect - and a separate project.

| Route family | Metric source |
| --- | --- |
| `team_record_leaderboard` | win percentage, by definition |
| `player_occurrence_leaders` | the named event |
| `team_occurrence_leaders` | the named event |
| `player_stretch_leaderboard` | the stretch metric, resolved upstream |
| `playoff_appearances` | appearance counts |
| `playoff_round_record` | round records |
| `record_by_decade_leaderboard` | decade records |
| `lineup_leaderboard` | the lineup metric |

## Blocker ids

Stable identifiers reported through `metadata.unsupported_filters`. They are
backend and test vocabulary, never product copy: each has human wording on the
card, and the frontend suppresses any note that names one.

| Id | Meaning |
| --- | --- |
| `leaderboard_metric_required` | a ranking was requested and named no metric |
| `leaderboard_multiple_metrics_unsupported` | more than one distinct metric was named |
| `leaderboard_aggregation_unsupported` | a season total was asked for a metric ranked per game |
| `leaderboard_metric_unavailable_for_scope` | the named metric cannot be computed for the requested window |
| `leaderboard_request_unclear` | part of the question is outside the stat-shaped grammar |

## Refusal metadata contract

Nothing ran, so nothing is published as the metric that did.

| Field | On a boundary refusal |
| --- | --- |
| `stat` | null or absent - never a metric, because no ranking executed |
| route `stat` kwarg | never set |
| `requested_stat` | the one explicit metric the refusal is about, for the aggregation and scope refusals only |
| `requested_metrics` | every distinct metric named, in query order, only when more than one was named |
| `requested_aggregation` | what the question asked for, on an aggregation mismatch |
| `available_aggregation` | what the metric's leaderboard actually ranks, on an aggregation mismatch |

`stat` is **null or absent**, not strictly absent: the metadata builder always
emits the key, and serializing it produces `"stat": null`. The guarantee the
product makes is the one that matters - no metric is ever published as the one
that ran - and it is tested that way rather than by key presence.

A refusal that could not read the whole question publishes neither
`requested_stat` nor `requested_metrics`: it has no complete reading of the
request to report, and a partial one presented as the request is the defect
this contract removes.

## Aggregation is metric-specific

Leaderboards are not uniformly per-game. The backing column decides whether a
requested season total is the thing that would actually run.

Compatibility is symmetric. Two things are decided independently - what the
question explicitly asked for, and what the selected column actually ranks -
and an explicit request must match. Asking for a total of a per-game column and
asking for a per-game figure of a total column are the same mistake pointing
opposite ways, and both refuse.

Requested aggregation is read from the query as one of `unspecified`, `total`,
`per_game` or `rate`. A rate word settles it before "average" is read as a
per-game request, so "average true shooting percentage" stays a rate question.

| Backing | Columns | `total X` | `X per game` / `average X` | rate wording |
| --- | --- | --- | --- | --- |
| `total` | `pf`, `minutes`, `fgm`, `fga`, `fg3a`, `ftm`, `fta` | answers | **refuses** | refuses |
| `per_game` | `pts`, `reb`, `ast`, `stl`, `blk`, `tov`, `fg3m`, `oreb`, `dreb`, `plus_minus`, `opponent_pts` | **refuses** | answers | refuses |
| `rate` | `*_pct`, `*_rating`, `pace` | refuses | refuses | answers |
| `count` | `games_played`, occurrence counts, `wins`, `losses` | refuses | refuses | refuses |

An unqualified question asks for no particular aggregation and keeps the
metric's established behavior: `personal fouls leaders` still ranks `pf_total`,
`points leaders` still ranks `pts_per_game`. A column with no classification
would silently pass every check, so every column in both leaderboard tables is
classified and a test fails if a new one is not.

Team leaderboards rank no season totals at all, so every team total refuses.

Because the metric decides, the route vocabulary and the detector vocabulary
have to agree on every form. A form the route documents but the detector cannot
reach becomes a different metric's question: `total three-point attempts
leaders` was read as a points request until the adjectival long form was added
alongside the `three-point makes` and `three point percentage` forms its
siblings already carried.
