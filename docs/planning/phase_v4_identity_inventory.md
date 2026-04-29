# Phase V4 Identity Inventory

> **Role:** Data, contract, and UI-target inventory for Phase V4 player
> imagery, team logos, and scoped team-color plumbing.

---

## Goal

Phase V4 should make player and team identity visible in the UI without moving
query semantics into React. The frontend may derive image URLs and scoped team
CSS variables from structured identity fields, but the engine/API must provide
the identity facts: ids, names, abbreviations, and context.

---

## Sources Reviewed

- `docs/architecture/design_system.md`
- `docs/reference/data_catalog.md`
- `docs/reference/result_contracts.md`
- `src/nbatools/query_service.py`
- `src/nbatools/api.py`
- `frontend/src/api/types.ts`
- `frontend/src/components/DataTable.tsx`
- `frontend/src/components/ResultEnvelope.tsx`
- `frontend/src/design-system/Avatar.tsx`
- `frontend/src/design-system/TeamBadge.tsx`
- Representative data headers under `data/raw/teams/`, `data/raw/rosters/`,
  `data/raw/player_game_stats/`, `data/raw/team_game_stats/`, and
  `data/processed/player_game_features/`

---

## Existing Identity Data

| Source | Grain | Available identity fields | Notes for Phase V4 |
| --- | --- | --- | --- |
| `data/raw/teams/teams_reference.csv` | One row per team/franchise reference entry | `team_id`, `team_abbr`, `team_name`, `city`, `active_flag` | Good active-team lookup. This is not the historical naming source. |
| `data/raw/teams/team_history_reference.csv` | One row per historical team identity range | `team_id`, `season_start`, `season_end`, `team_abbr`, `team_name`, `city`, `franchise_label` | Canonical for historical team naming. `team_id` is the identity key; names/abbreviations are presentation/history fields. |
| `data/raw/rosters/<season>.csv` | One row per player-team-season-stint | `season`, `team_id`, `team_abbr`, `player_id`, `player_name`, jersey/position/profile fields | Good season-level player identity source. No headshot URL field exists. |
| `data/raw/player_game_stats/<season>_<season_type>.csv` | One row per player per game | `player_id`, `player_name`, `team_id`, `team_abbr`, `team_name`, `opponent_team_id`, `opponent_team_abbr`, `opponent_team_name` | Strongest game-level player/team/opponent identity source. |
| `data/raw/team_game_stats/<season>_<season_type>.csv` | One row per team per game | `team_id`, `team_abbr`, `team_name`, `opponent_team_id`, `opponent_team_abbr`, `opponent_team_name` | Strongest game-level team/opponent identity source. |
| `data/processed/player_game_features/<season>_<season_type>.csv` | One row per player per game | `player_id`, `team_id`, game/season fields | Feature table keeps ids but not display names or abbreviations. It should not become an imagery contract by itself. |
| `frontend/src/styles/team-colors.json` | One row per active team abbreviation | `primary`, `secondary` by `team_abbr` | Presentation map only. It should feed scoped CSS variables, not engine semantics. |

No current dataset stores image URLs. Phase V4 should derive player headshot and
team logo URLs in frontend presentation helpers from stable ids, with fallbacks
when ids or images are unavailable.

---

## Structured Result Row Inventory

Result sections already carry useful identity fields inconsistently:

- Player game finder rows include `player_name`, `player_id`, `team_name`,
  `team_abbr`, `opponent_team_name`, and `opponent_team_abbr`, but not
  `team_id` or `opponent_team_id` in the output projection.
- Team game finder rows include `team_name`, `team_abbr`,
  `opponent_team_name`, and `opponent_team_abbr`, but not `team_id` or
  `opponent_team_id` in the output projection.
- Top-player-game rows include `player_name`, `player_id`, `team_abbr`,
  `opponent_team_abbr`, `game_id`, and date/context fields.
- Team leaderboard rows include `team_name`, `team_abbr`, and `team_id`.
- Summary rows aggregate around display fields such as `player_name` or
  `team_name`; they do not consistently retain `player_id`, `team_id`,
  `team_abbr`, or opponent identity fields.
- Player leaderboard code has helpers for latest `player_id` -> `team_id` /
  `team_abbr` context, but that does not mean every rendered row exposes every
  identity field needed by the UI.

Phase V4 should avoid relying on display-string parsing. If a renderer needs an
id to build imagery, the API response should carry that id explicitly in either
metadata context or row data.

---

## API And Metadata Inventory

Current API response shape:

- `QueryResponse.result.metadata` carries display/context fields such as
  `player`, `players`, `team`, `teams`, `opponent`, `season`, `season_type`,
  `route`, and `query_class`.
- `frontend/src/api/types.ts` mirrors those display fields but does not define
  structured identity objects.
- `src/nbatools/query_service.py` builds natural and structured metadata from
  parsed slots/kwargs. It currently records player/team/opponent display values,
  not stable ids or abbreviation/name/id bundles.
- `docs/reference/result_contracts.md` already names the target contract:
  `player_context`, `team_context`, and `opponent_context`.

Recommended additive metadata fields for Phase V4:

| Field | Shape | Purpose |
| --- | --- | --- |
| `player_context` | `{ player_id, player_name }` | Single primary player subject when known. |
| `players_context` | Array of `{ player_id, player_name }` | Multi-player comparisons or leaderboards when a bounded subject list exists. |
| `team_context` | `{ team_id, team_abbr, team_name }` | Single primary team subject when known. |
| `teams_context` | Array of `{ team_id, team_abbr, team_name }` | Multi-team comparisons or bounded team lists. |
| `opponent_context` | `{ team_id, team_abbr, team_name }` | Opponent filter identity when known. |

These fields should be additive. Existing `player`, `players`, `team`, `teams`,
and `opponent` display fields should remain stable for current consumers.

---

## Current Frontend Identity Call Sites

| Surface | Current owner | Current behavior | Phase V4 target |
| --- | --- | --- | --- |
| Result metadata player chip | `frontend/src/components/ResultEnvelope.tsx` | Renders `Avatar` from `metadata.player` display string only. | Use `player_context.player_id` for `Avatar.imageUrl`; keep initials fallback. |
| Result metadata team/opponent chip | `frontend/src/components/ResultEnvelope.tsx` | Renders `TeamBadge` from `metadata.team` or `metadata.opponent`; abbreviation is inferred from display string shape. | Use `team_context` / `opponent_context` for logo URL, abbreviation, and display name. |
| Result metadata arrays | `ResultEnvelope.tsx` | `metadata.players` and `metadata.teams` render as joined text, not per-entity identity chips. | Keep text in Phase V4 unless bounded context arrays make per-entity chips straightforward and tested. |
| Player table columns | `frontend/src/components/DataTable.tsx` | `player_name` / `player` columns render fallback `Avatar` from the formatted name. | Pair display columns with row `player_id` when present; fall back to initials when absent. |
| Team/opponent table columns | `frontend/src/components/DataTable.tsx` | `team`, `team_name`, and `opponent` columns render `TeamBadge`; abbreviation is inferred from the formatted value. | Pair display columns with row `team_id`, `team_abbr`, `opponent_team_id`, and `opponent_team_abbr` when present. |
| Shell/result surface theming | `frontend/src/App.tsx`, `App.module.css`, `ResultEnvelope.tsx` | Uses global neutral/orange tokens only. | Apply scoped `--team-primary` / `--team-secondary` only for safe single-team contexts. |
| Empty/loading/no-result states | Existing state components | No player/team identity rendering. | No Phase V4 identity target unless a future first-run item explicitly adds one. |

Primitive capability:

- `Avatar` already accepts `imageUrl` and `unavailable`, but it does not own an
  image-source policy.
- `TeamBadge` already accepts `logoUrl` and reads `--team-primary` /
  `--team-secondary` through CSS, but it does not own team lookup or theming
  policy.

---

## Target UI Locations And Owners

| Target | Owner path | Identity needed | Fallback rule |
| --- | --- | --- | --- |
| Single-player metadata chip | `ResultEnvelope.tsx` | `player_context.player_id`, `player_context.player_name` | Initials avatar using display name. |
| Single-team metadata chip | `ResultEnvelope.tsx` | `team_context.team_id`, `team_context.team_abbr`, `team_context.team_name` | Text badge using abbreviation/name. |
| Opponent metadata chip | `ResultEnvelope.tsx` | `opponent_context.team_id`, `team_abbr`, `team_name` | Text badge using abbreviation/name; do not make opponent the whole result theme. |
| Player entity cells | `DataTable.tsx` | Row `player_id` plus `player_name`/`player` | Initials avatar using the formatted cell value. |
| Team/opponent entity cells | `DataTable.tsx` | Row `team_id`/`team_abbr` or `opponent_team_id`/`opponent_team_abbr` plus display name | Text badge using the formatted cell value. |
| Single-team result accent | Result-region wrapper or `ResultEnvelope`-adjacent presentation code | One safe `team_context` and color map entry | Neutral result surface if no single safe team exists. |
| Multi-team result rows | `DataTable.tsx` and query-class section components | Per-row team identity where present | Row/badge identity only; no page-level team theme. |

---

## Fallback Semantics

- **Missing player id:** render the existing initials avatar. Do not attempt to
  infer ids from names in the frontend.
- **Broken or unavailable player image:** fall back to initials without changing
  row height or label text. The implementation can use primitive-local image
  error state, but the policy remains presentation-only.
- **Missing team id with known abbreviation:** render a text `TeamBadge` and
  use colors only if the abbreviation is present in `team-colors.json`.
- **Missing team id and abbreviation:** render a neutral text badge from the
  display value.
- **Historical teams:** prefer season-aware `team_history_reference` identity
  from the engine/API. If no logo/color mapping exists for a historical
  abbreviation, use neutral fallback rather than active-team colors by guess.
- **Opponent teams:** logos are allowed in opponent chips and opponent table
  cells. Scoped result theming should use the primary team subject, not the
  opponent of a player query.
- **Multi-player comparisons:** show per-row/player identity where ids are
  present. Do not add a single dominant player visual theme.
- **Multi-team comparisons and leaderboards:** show row/badge logos where
  identity is present. Do not apply a page-level or card-level team color theme.
- **No-result/error states:** keep neutral unless the engine explicitly returns
  a safe identity context with the no-result payload.

---

## Contract Gaps To Close

1. Query metadata needs additive structured identity fields (`player_context`,
   `team_context`, `opponent_context`, and bounded plural variants) so metadata
   chips do not parse display strings.
2. Some result row projections drop ids that source data already has, especially
   team/opponent ids in finder rows and identity ids in aggregate summary rows.
3. The frontend needs a typed, deterministic identity helper for asset URL
   generation, team color lookup, and scoped CSS variable output.
4. `Avatar` and `TeamBadge` need reliable image-error fallback behavior before
   external assets are used broadly.
5. Team color application needs a single-team context guard so multi-team
   leaderboards, comparisons, and mixed player-vs-opponent views remain neutral.

These are Phase V4 implementation tasks. This inventory changes no runtime
behavior.
