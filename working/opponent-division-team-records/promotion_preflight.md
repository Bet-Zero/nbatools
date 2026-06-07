# Opponent-Division Team Record Promotion Preflight

## Unsupported Boundary Before

Named-team NBA division record phrases such as `Celtics record vs Atlantic
Division`, `Lakers record against Pacific Division`, and `Knicks record vs
Central Division` returned `no_result` / `filter_not_supported` with
`metadata.unsupported_filters=["opponent_division"]`. The guard preserved the
`team_record` route and prevented fallback to a broad team record or a
conference-only record.

## Accepted Phrases

- `Celtics record vs Atlantic Division`
- `Lakers record against Pacific Division`
- `Knicks record vs Central Division`
- Equivalent named-team `against` / `vs` / `versus` division phrasing for the
  six NBA divisions in trusted current-era regular seasons.

## Rejected / Guarded Phrases

- `record against Northwest Division teams` -> no-subject division phrasing
  remains unsupported on `team_record_leaderboard` with
  `unsupported_filters=["opponent_division"]`.
- `Lakers record against Western Conference Pacific Division teams` -> mixed
  conference-plus-division phrasing remains unsupported with
  `unsupported_filters=["opponent_division"]`.
- `Celtics playoff record vs Atlantic Division` -> playoff division record
  phrasing remains unsupported with `unsupported_filters=["opponent_division"]`.
- `Celtics conference finals record vs Atlantic Division` -> playoff-round
  phrasing continues to use the single-team playoff-round unsupported boundary.
- Geography phrases such as `east coast teams` remain unsupported with the
  existing opponent-conference geography guard.
- Seasons without trusted membership coverage return `no_result` /
  `filter_not_supported` with `unsupported_filters=["division_coverage"]`.

## Expected Route

Accepted named-team regular-season division phrases route to existing
`team_record`.

## Required Data Contract

No new dataset is required. Execution uses
`data/raw/teams/team_conference_membership.csv`, which already has one trusted
season-team row with required `division` values for `2024-25` and `2025-26`.
The durable data contract must be updated to name opponent-division
`team_record` as a supported consumer and to define the missing/untrusted
division coverage behavior.

Required R2 key: `raw/teams/team_conference_membership.csv`.

## Result Contract

Accepted queries reuse the existing `team_record` result contract:

- sections: `summary`, `by_season`
- metadata includes `opponent_division`, `opponent_team_abbrs`, and no
  `unsupported_filters`
- applied filters include `kind=division`, `label=Opponent division`, and the
  normalized division name
- caveats use the existing opponent-list wording from `team_record`

No new frontend section or result shape is introduced.

## Parser And Collision Checks

Touched collision groups:

- opponent conference vs division vs geography phrases
- team record vs team record leaderboard
- team record vs playoff round record

Accepted division phrases must not re-enable conference parsing for mixed
conference-plus-division text. No-subject, playoff, and conference-finals
division siblings remain pinned as unsupported boundaries.

## Raw QA Plan

Convert these accepted cases from unsupported to execution-backed `team_record`:

- `celtics_atlantic_division_guard`
- `lakers_pacific_division_guard`
- `knicks_central_division_guard`

Keep these rejected cases unsupported:

- `record_against_northwest_division_teams_guard`
- `lakers_western_conference_pacific_division_guard`
- `celtics_playoff_atlantic_division_guard`
- `celtics_conference_finals_atlantic_division_guard`
- existing geography guard

Add or keep a missing-coverage case for historical division membership.

## Frontend / Visual QA

Rendering unchanged. The existing `team_record` renderer is reused. No new
layout or frontend-copy path is required beyond the applied filter label.

## Release Docs

Update:

- `docs/reference/data_contracts.md`
- `docs/reference/data_catalog.md`
- `docs/reference/query_catalog.md`
- `docs/reference/query_guide.md`

