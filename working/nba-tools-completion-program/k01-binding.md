# K01 identity and covered-scope binding

This binds the existing Core-1 K01 obligations, not a second queue. The original
pre-tuning preparation below is retained; current execution evidence follows. Raw expectations
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

## Current execution and qualification

The original13selectors were frozen in local172101c before runtime alias changes.
Historical oracle was independently frozen by /root/availability_checker before
interpreter execution: originalSHAe10364a31c47656b5af1ce659d46b726c71658b6b02eeb01ef03b7d6efca0fef.
Source run39086850054 retained10CSV; expanded run39091056182 retained16CSV,
including six historical team files needed to verify displayed Ewing W/L.
Expanded reviewedb00441dde694e29e0676b32422b9c30087c9749b,
requestd5323bc75bbec5aeeb1965d1158f0f79368a0311,
artifact12123205436 ZIPa934572314673d4ee094c69a9f914df8f341fa9bcd41c04b24c1d5d7980d9978.
Both requiredsource runs selected/executed/passed1 withzero skips/errors.
The pinned generation lacks player_names.csv; no fabricated index was used.
Tracked tests/k01_historical_expected.json is the independent oracle extended only
with canonical team-file W/L joins (SHAded324dd5c9462694170bb92883e3343cc53fe4d116de08dc529bfaf420b6152).

Marcus201173/SAS:1game0PTS/REB/AST,1–0; unqualified Marcus200766:53games,
313PTS101REB140AST,21–32. SEA2007:82games20–62,7999PTS3659REB1748AST;
OKC2008:82games23–59,7952PTS3496REB1663AST. Franchise union164games43–121,
15951PTS7155REB3411AST. Ewing121 covered1996–2001:348games205–143,
5027PTS2928REB412AST. This is explicitly not his complete pre-1996 career.

Baseline13queries: A/B/C and current-franchise cases already correct. Explicit
Seattle SuperSonics was unresolved; three historical aliases now preserve SEA
scope instead of widening to OKC. Six missing team files initially prevented
local Ewing replay; acquisition resolved the local dependency without changing
statistical runtime. All13cached exact-key/raw arithmetic checks subsequently passed.

Checker supplied fresh accented Jović, renamed Portis on the older spelling,
reordered Marcus/Spurs and full Thunder wording; these passed. Clear 'What record
did the Sonics finish with in2007-08?' failed because 'with in2007-08' was treated
as an unknown teammate. It is now D1_wording regression14, with antecedent-record
preposition handling requiring the entire following tail to be understood scope.
Unknown people/extra clauses remain protected. The original underspecified 'how
did the Sonics finish?' remains an open ambiguity/delivery finding, not a passing
record or standings answer. Do not relabel repaired wording as unseen evidence.

Required request: tests/test_k01_identity_real_data.py14cases and14RawQA IDs
k01_a1_plain, k01_a1_accent, k01_a1_alias, k01_a2, k01_b1, k01_b1_collision,
k01_c1_old, k01_c1_new, k01_c1_union, k01_d1, k01_d1_era, k01_d1_wording,
k01_e1, k01_e1_season. Final preflight8060passed1507skipped141.20s;172focusedidentitytests1skip and11controlledalias/grammar tests passed. Independent checker accepted14cached exact-key cases, source arithmetic, freshidentity wordings and narrowpreposition safeguards. Actualrunner/CI/deployed acceptance remains pending.

Actual required run39091879839 accepted by independentchecker:14selected/executed/passed,
zero skips/errors;14RawQA137checks. Reviewedc35fb4e936b70f7a466bc61046ac8ab73e8faaaf,
requestb3cfb61c48d062b15f1e9a280237caf4e0be707c. Numericartifact12123306587
ZIPf94e85828d42c8fb6e33418c2a751a78b63ec6f0cbb6c6b7083acdf3da749b0c;
QA12122918605 ZIP42c182e5234ff480785995c7d394e91b4d43fd2becd933f817d41133da726795.
CandidateCI39091852784passed. Literalhumanreviewfields remainpending/unreviewed.

Localactualbrowser20responses across1280desktop/390mobile hadnoJSerrors/pageoverflow;
visualinspection foundpartialcareer scope hiddenunderDetails. Frontendnow displays
source-derivedcoveredgame years andcoverage boundary besidehero; searchedseasons
are labeledseparately. Twofinalbrowserresponses verifythisfix. Fullfrontend443tests
passed afterlockedinstall, pluslint/build. [Compactbrowserreceipt](k01-browser-verification.json)
retainsqueries,scope,hashes andlimits. ActualThunder two-seasonhero alreadycorrect;
shorterRawQA hero is snapshot-only. Productionbrowser access isblocked bycloudproxy403;
useexistingGitHubActions forproductionverification, not anowneraccessrequest.
Finalfrontend-only changes awaitnormalCI; no backendnumericbehavior changed.
