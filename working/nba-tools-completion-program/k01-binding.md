# Proposed K01 binding — preparation only

This binds the existing Core-1 K01 obligations, not a second queue. No interpreter
was run, no runtime changed, and no I/N/L/D acceptance is asserted. Raw expectations
below were selected independently by player_id from retained pinned-generation
`queue-d-production-0574735-20260716` CSVs. All queries request Regular Season.

## Fixed finite cases and existing selectors

| Proposed ID | Intended query/meaning | Existing precise anchors | Can proceed locally? |
|---|---|---|---|
| K01-A1 | “Nikola Jokic stats in 2023-24” and “Nikola Jokić stats in 2023-24” mean the same player203999 and whole named season. Add ordinary nickname “Joker's 2023-24 averages” as alias language control, without changing its identity truth. | `tests/test_entity_resolution.py::TestResolvePlayer::test_nikola_jokic_no_accent`; `tests/test_player_identity_selection.py::test_accent_variants_of_one_player_are_one_player`; `tests/test_player_game_summary_filters.py::test_player_filter_normalizes_accents_spacing_case_and_dash_variants` | Yes: full2023-24 player/team rows retained. |
| K01-A2 | “Nikola Jovic stats in 2024-25” must resolve Jović1631107, never Jokić203999. | `tests/test_player_identity_real_data.py::test_named_season_summary_matches_raw_rows` (select existing Nikola Jovic2024-25 parameter); `tests/test_player_identity_selection.py::test_canonical_name_is_the_latest_spelling_keeping_accents` | Player-only numeric truth available now; team2024-25 rows needed if asserting W/L separately. |
| K01-B1 | “Marcus Williams Spurs stats in 2007-08” selects201173 with SAS team scope, not200766 or the combined names. Companion unqualified collision must state the existing deterministic selection/ambiguity policy, never merge identities. | `tests/test_player_identity_real_data.py::test_shared_name_with_a_team_picks_that_teams_player`; `tests/test_player_identity_selection.py::test_team_narrows_a_shared_name_to_the_player_on_that_team`; `test_shared_name_keeps_one_player_with_most_games_and_says_so`; `test_tie_on_games_goes_to_the_most_recent_player` | Controlled fixtures yes; actual historical source absent from retained files checked. Acquire pinned2007-08 player/team CSVs before freezing numeric totals. |
| K01-C1 | “Bobby Portis stats in 2024-25” and “Bobby Portis Jr. stats in 2024-25” both select1626171, all49 rows even though the old spelling differs. Cross-season control2023-24+2024-25 must not split a person into two identities. | `tests/test_player_identity_real_data.py::test_renamed_player_keeps_every_game_of_the_season`; `test_season_leaderboard_lists_a_renamed_player_once`; `tests/test_player_identity_selection.py::test_spelling_known_only_from_other_seasons_still_finds_the_player`; `test_every_spelling_of_one_player_is_kept` | Yes: both player seasons retained; no acquisition needed for game counts and PTS/REB/AST. |
| K01-D1 | “Thunder record from2007-08 through2008-09” follows franchise1610612760 across SEA andOKC; include earlier-Seattle caveat. “Seattle SuperSonics record in2007-08” remains era-specific. Do not use current alias as a row-abbreviation-only filter. | `tests/test_c2_franchise_identity.py::test_current_abbreviation_names_the_franchise_id`; `test_team_mask_keeps_earlier_names_of_the_franchise`; `test_caveat_names_the_earlier_seasons`; `test_name_by_latest_franchise_merges_earlier_names` | Controlled fixtures yes. Actual2007-08 and2008-09 team CSVs absent locally; acquire pinned files and select franchiseID before calculating. |
| K01-E1 | “Patrick Ewing career stats” may report only the covered1996-97 onward portion for ID121. It must explicitly say covered/partial career and must not combine Patrick Ewing Jr.201607. Single-season counterpart must not falsely call itself a partial career. | `tests/test_player_identity_real_data.py::test_hall_of_famer_is_the_default_for_his_shared_name`; `tests/test_c2_history.py::test_career_answers_label_the_covered_span`; `test_single_season_answers_carry_no_career_label` | Fixture span-label control available; actual Ewing rows absent locally. Needs pinned1996-97 through2001-02 player files plus manifest/identity coverage establishing full available span; no invented pre1996 totals. |

The B1 same-name policy must follow existing repository semantics, not an invented
new preference. Existing tests allow a deterministic one-ID choice plus an explicit
collision note for unqualified names. Team-qualified positive B1 must execute.
Historical source identities in B1/D1/E1 above are proposed from existing repository
contracts, not independently reacquired source facts yet.

## Independently computed available raw truth

Select exact ID, named season and Regular Season; compare every game/team/player
key, not name-string matching alone. Means may round to0.001 absolute tolerance.
Key hashes use SHA256 of compact JSON of sorted integer `[game_id,team_id,player_id]`
triples (sort columns in that order).

| Case/source | Rows | PTS/REB/AST sums | PTS/REB/AST means | Exact key-set SHA256 |
|---|---:|---|---|---|
|203999,2023-24,Jokić|79|2085/976/708|26.392405/12.354430/8.962025|`d9b737266eff8066eacc7a15917a273e348992626f9e6cf78d80bde352384a71`|
|1631107,2024-25,Jović|46|494/180/131|10.739130/3.913043/2.847826|`982a6efdd890b8d789690016f92ca487606888001329938f06b1c3e0a01bc202`|
|1626171,2023-24,Bobby Portis|82|1130/607/104|13.780488/7.402439/1.268293|`2c187e487b0e11b00fb2a1eec398664ab864a6156d9d0ef27dde915a4e70bacf`|
|1626171,2024-25,Bobby Portis Jr.|49|680/411/104|13.877551/8.387755/2.122449|`6e1add83e579938e581df7366c4f2c8b425adec7b2cb121f3854efc1557d4c4e`|

Portis cross-season union:131rows,1810PTS/1018REB/208AST. This union is explicitly
those two named seasons, not his full career. Each season has one spelling;
identity persistence is proven by the common source ID.

Retained source root `/workspace/work/s4-local-replay/data/raw/player_game_stats`:

- `2023-24_regular_season.csv`: SHA256 `a455e553ceb0b4e74bd4caf37aca482c0a9aab193631b6f2b383b623f861d760`.
- `2024-25_regular_season.csv`: SHA256 `3a259df8b93029e0d809ce38b8123d98a3f0f009017ec6d43e0b285906cf6591`.

## Exact next source requirements and limits

1. Pinned generation manifest and `metadata/player_names.csv` to bind identity and
   actual covered season inventory, not the SDK catalog alone.
2. `raw/player_game_stats/2007-08_regular_season.csv` and matching team file for
   same-name scope and independent W/L if displayed.
3. `raw/team_game_stats/{2007-08,2008-09}_regular_season.csv` for franchise transition.
4. `raw/player_game_stats/{1996-97,1997-98,1998-99,1999-00,2000-01,2001-02}_regular_season.csv`
   for the covered Ewing segment. Validate manifest coverage and identity-index
   references; do not silently skip missing requested files as a complete career.

Fetch through existing read-only pinned R2 runner, retain bytes/checksums and freeze
arithmetic before query execution. These missing subsets are independent of the
ready A/C controlled and numeric work. Existing helper `_raw_regular_rows` skips
missing files, so add explicit expected file availability for K01 acceptance;
otherwise a smaller available subset could pass against itself.

Unfinished: precise committed new positive selectors/corpusIDs; actual historical
numeric oracles; current candidate tests/CI; language evaluation without tuning its
questions; independent meaning review; actual deployed/desktop/mobile coverage and
partial-career label rendering. No historical or human acceptance is implied by
this preparation memo.
