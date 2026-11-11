# Whole-game P.J. Washington rebound correction (v7)

Resolves [DQ-auto-e148abf7…](../../data-quality/DQ-auto-e148abf704eadc650f2348d031a9c18214073054848a48a6b9d242d84f0ffb1d.json)
on top of merged main `cf39739` (PR604/PR605). This is an isolated, provisional
development version. **No production data, R2 publication or active pointer changes.**

## What changed

[apply_whole_rebound_correction.py](apply_whole_rebound_correction.py) extracts the
unchanged v6 archive (`b2c34ea7…`, manifest `e46b6748…`), authenticates it with
`DevelopmentSnapshot`, and writes a **new** version `current123-whole-rebound-development-v7`
([binding.json](binding.json), [correction.json](correction.json)). Exactly two cells in one raw
file change, on CSV line 2668 of `data/raw/player_game_stats/2026-27_regular_season.csv`:

| Key | Field | v6 | v7 |
| --- | --- | --- | --- |
| game 0022600184 / team 1610612742 DAL / player 1629023 | dreb | 5 | 6 |
| same | reb | 9 | 10 |

OREB 4 and the other 14 whole-game counts already equal the official scorer line and are
asserted unchanged. Every other v6 file is byte-identical; two metadata files are added
(the correction record and a passing `build_slice_manifest` report). v6 and all older
versions stay in the repository and still load with their original values.

## Evidence (retained; nothing collected again)

- Official scorer report PDF `5d11d197…` (FINAL BOX page 0, literal line
  `25 P.J. Washington F 39:00 7 18 3 8 4 5 4 6 10 …`), already qualified in PR602.
- PR602-reviewed independent oracle `7d054703…`, whose whole-game scorer row is OREB 4 / DREB 6 / REB 10.
- Separate check: after correction, the summed DAL player DREB/REB (32/50) equal the
  unchanged team row for game 184. All 246 team-games in the season now reconcile; v6 had
  this as the only mismatch (31/49). Washington's Q1–Q4 period rows also now sum to 6/10.
  Page 5 of the book ("1st QUARTER – 3rd QUARTER") shows 4/5/9, which is where the old
  whole-game value matches; that's a likely origin, recorded here but not relied on.

## Dependent values

- Query-time consumers read the corrected row: game totals, season sums/averages,
  thresholds/filters, rankings, streaks and double-double classification.
- Stored derived inputs: the only processed consumer of player REB is
  `player_game_features.reb_last_5`, built from *prior* games. Game 184 is
  Washington's last game at the fixed 123-game cutoff. The script rebuilds with the
  existing builder before and after the correction and asserts identical output, so
  the correct recalculation is no change. The retained v6 processed bytes are kept,
  because a rebuild with the current pandas adds unrelated float-format churn in 28 rows.
  Team, game and league builders read only `team_game_stats` (unchanged).
- Not changed: `player_season_advanced` (an official season-level source table) and its
  season `reb_pct` attached to finder rows; period rows (already corrected in v5); the 484
  unknown rate cells; DQ-006 membership.

## Verification

`tests/test_whole_rebound_correction.py` (8 controls). Its expectations come from the
book line and from plain pandas over the pinned rows, never from app output, and it runs
on both v6 and v7:

| Consumer | v6 | v7 |
| --- | --- | --- |
| Rebounds on 2026-11-04 (natural, structured, HTTP) | 9 | 10 |
| Season REB / DREB sum (8 games) | 63 / 46 | 64 / 47 |
| Season REB / DREB per game | 7.875 / 5.75 | 8.0 / 5.875 |
| Games with 10+ rebounds include game 184 | no | yes |
| Double-doubles (21 PTS / 10 REB) | 1 | 2 |
| Season total-rebound and double-double leaderboards (value, tie-consistent rank) | 63 / 1 | 64 / 2 |

Hosted required numerical wrapper: `tests/cloud_whole_rebound_correction_real_data.py`.
The PR records the review, CI and R2 receipts.
