# Data Contracts

This document defines the core dataset contracts for `nbatools`.

Setup-qualified cloud archive route (PR502): `tools/cloud_nba_archive.py` retains
original NBA Stats JSON from the immutable SportsDataverse mirror revision,
CC BY 4.0 attribution and per-file SHA256 receipts before conversion. Existing
games/team/player producers accept explicit source frames through `raw_frame`;
their default direct acquisition and canonical grains are unchanged. The bounded
2025-26 regular-season CLE–NYK slice has 1 game, 2 paired team rows, 21 player-game
rows and 21 separately trusted starter-role rows; existing builders produce
game/team/player features. Legacy player-stat starter flags from logs without
positions are not verified roles. Source receipts/original payloads and outputs
are permanently retained together in the Git staging ZIP named in the pipeline
runbook. Download time is not original capture time or proof of current freshness.
The raw archived PBP is retained but fails the existing score/key contract;
period/on-off coverage is not supplied by this route. This does not authorize
publishing an incomplete season or replacing an immutable production snapshot.

A separate bounded cloud archival check used the unchanged LeagueLineupViz
normalizer/validator on the mirror's exact `GroupQuantity=5`, `MinutesMin=10`,
2025-26 regular-season payload: 2,594 rows across 30 teams. Every five-player ID
list and numeric field matched the retained source in independent checking.
This qualifies that source threshold only, not sub-10-minute lineups, independent
roster completeness or current freshness. Original JSON, canonical CSV,
attribution and hashes are retained together in `lineup-archive-staging.zip`
with its receipt in PR502. No new lineup runtime behavior or publication.

Additional manual season-input qualification (PR505) retains original official
Advanced/PerGame player/team tables and standings, applies the unchanged existing
normalizers, and preserves582/30/30 canonical2025-26 rows with as-of date from the
accepted completed-game capture. Independent W/L reconciliation covers all30teams;
source team MIN is not used as player minutes-per-game. Source capture time remains
unknown. The incomplete29team roster stays outside canonical rosters and does not
establish historical membership. The official2026-27 schedule remains planning
source JSON: future/TBD rows never become Final in the completed-game contract.
These inputs do not provide exact period/on-off data or full current freshness.

The existing publication-derived `metadata/player_names.csv` has one distinct
`(player_id, player_name, season)` row across both game season types, with
`first_seen` preserving source order. It is generated from all staged player-game
files by `_write_player_names`, not from roster snapshots. Named multi-season
loads may use the union of seasons for **every** matching ID and spelling to
exclude irrelevant files before reading. Actual game rows still determine
identity selection, team filtering, sample values and ambiguity notes; requested
search spans and partial-career disclosures remain explicit. Missing/malformed
season metadata, unavailable season coverage, unknown identities and empty
intersections retain a full scan. A well-formed arbitrary list is not completeness
proof: use the authenticated publication producer and qualified generation.
K12 independently reconciled the existing immutable index against all60served
player-game files/786,773rows:14,581valid named tuples and their order match
exactly. Three nameless rows for unindexed ID2179 remain outside that index's
valid-name contract and cannot establish an identity. This index is neither
historical roster membership nor evidence of absence, injury or status.

The goal is to keep query behavior stable as the repo grows. Commands should depend on explicit dataset contracts, not on accidental columns or vague assumptions.

This is a living document. Update it whenever:

- a dataset grain changes
- required columns change
- a new derived dataset becomes a core dependency
- a command starts depending on a new dataset or field

---

## Contract rules

For each dataset, this document should define:

- path pattern
- grain
- key fields
- required columns
- important derived columns
- producer(s)
- consumer(s)

### General rules

- commands should only depend on documented required columns
- optional columns should be treated as optional, never assumed
- sample-aware metrics must document their source dataset
- new derived datasets should be added here before they become widely depended on
- new datasets should be additive, clearly scoped, and placed in the correct lifecycle layer (`raw`, `processed`, or `derived`)
- extending an existing canonical dataset requires explicit rationale and must not silently repurpose the table's contract
- trust and coverage fields are required for partially supported or gated execution paths
- mixed-grain semantics (for example, game-level with stint-level or play-by-play-derived rows) must not be hidden inside legacy tables without an explicit approved contract

---

## 1. `player_game_stats`

### Path pattern

`data/raw/player_game_stats/{season}_{season_type_safe}.csv`

Examples:

- `data/raw/player_game_stats/2025-26_regular_season.csv`
- `data/raw/player_game_stats/2024-25_playoffs.csv`

### Grain

One row per **player-game**.

### Key fields

- `game_id`
- `player_id`

Recommended uniqueness expectation:

- unique on (`game_id`, `player_id`)

### Required columns

These are the baseline fields query behavior should be able to rely on:

- `game_id`
- `game_date`
- `season`
- `season_type`
- `player_id`
- `player_name`
- `team_id`
- `team_abbr`
- `team_name`
- `opponent_team_abbr`
- `matchup`
- `wl`
- `minutes`
- `pts`
- `reb`
- `ast`
- `stl`
- `blk`
- `tov`
- `fgm`
- `fga`
- `fg3m`
- `fg3a`
- `ftm`
- `fta`
- `plus_minus`

### Important derived/query fields

Some commands may also rely on these fields if they are present or built during processing/loading:

- `is_home`
- `is_away`
- `fg_pct`
- `fg3_pct`
- `ft_pct`
- `efg_pct`
- `ts_pct`

### Producer(s)

- raw ingestion commands that pull player game logs from the NBA data source
- any cleanup/standardization layer that normalizes the raw pull into the contract above

### Primary consumer(s)

- `player_game_finder`
- `player_game_summary`
- `player_compare`
- `player_split_summary`
- `player_streak_finder`
- natural-query player finder/summary/comparison/split/streak routes
- grouped boolean execution over player game samples

### Notes

This is one of the most important datasets in the repo.

Legacy `start_position` and `starter_flag` columns may appear in the current raw file because the historical `LeagueGameFinder` pull shape exposed a `START_POSITION` column name. They are not authoritative for starter / bench execution and must not be treated as a role contract.

For a neutral game whose canonical `games` row has no trusted home/away
designation, both participant rows use `is_home=0` and `is_away=0`. Neutral
participants must not be mislabeled as two away teams; trusted venue-relative
filtering remains owned by the canonical game identity contract.

Explicit two-player comparisons can apply one shared historical playing-for
team filter, separately from one scalar opponent, in a named regular season.
Complete canonical operand spans are read independently of sample modifiers:
`Compare A and B for the Lakers against Warriors` and `How did A and B compare
for the Lakers against Warriors?` both retain A, B, own teamLAL and opponentGSW.
The existing `player_compare` consumer independently selects each player's
actual team-game appearances; neither simultaneous membership/coappearance nor
head-to-head is implied. Static date/venue restrictions and fully consumed common
count predicates retain their existing selection order. Metadata keeps both
canonical player contexts and separate historical `Playing for` / `Opponent`
filter labels; a missing second operand never becomes a single-player finder.
A complete operand binds to one canonical data ID before team filtering. Exact
name identities take precedence over uniquely ID-bound omitted-suffix variants;
shared team context cannot guess between ambiguous identities. The final route
must retain both subjects, comparison grain and every consumed static sample
field. Multiple venue/window/date fragments with no equivalent single consumer
remain unfinished and yield no partial team-grain or first-window answer.

For this new comparison slice, exact threshold spans on the existing integer
count vocabulary PTS/REB/AST/FG3M/STL/BLK/TOV lower mathematically to equivalent
inclusive integer bounds through Decimal ceil/floor rules. Strict lower uses
floor+1, inclusive lowerceil; strict upper uses ceil-1, inclusive upperfloor.
Original normalized predicate text/operator/cutoff remain visible in `Count
filter`; differing bounds are explicitly labeled as equivalent integer execution.
Exact consumers retain original numeric lexemes as JSON-safe internal bound
strings when requested, including precise original-game minutes and MIN+count
checks; Decimal comparisons and labels avoid a float round-trip. Default legacy
threshold dictionaries remain unchanged. Negative
resulting ceilings and ranges containing no integers remain real empty samples,
not absolute values or dropped clauses. A partial-empty comparison keeps a
zero-games summary row with null per-game averages and additive sums0 while the
other independent sample exists; both-empty yields `no_match`. These are observed
appearance-sample aggregates, never invented DNP player rows or absence evidence.
Fractional/rate/time metrics outside this count domain, differently owned team
filters per player, and the new shared-team plus opponent-union composition
remain distinct unfinished positives. Existing no-team opponent unions remain
supported. Source/consumer/numeric addendum and retained obligations live under
`tests/fixtures/player_comparison_team_scope/`.

Player sample-aware metrics such as:

- USG%
- AST%
- REB%

ultimately depend on filtered player-game samples built from this contract and season-level supporting context.

---

## 1A. `player_game_starter_roles`

### Path pattern

`data/raw/player_game_starter_roles/{season}_{season_type_safe}.csv`

Examples:

- `data/raw/player_game_starter_roles/2025-26_regular_season.csv`
- `data/raw/player_game_starter_roles/2024-25_playoffs.csv`

### Grain

One row per **player-game role observation**.

### Key fields

- `game_id`
- `player_id`

Recommended uniqueness expectation:

- unique on (`game_id`, `player_id`)

### Required columns

- `game_id`
- `season`
- `season_type`
- `team_id`
- `player_id`
- `starter_position_raw`
- `starter_flag`
- `role_source`
- `role_source_trusted`
- `starter_count_for_team_game`
- `role_validation_reason`

### Important derived/query fields

- `team_abbr`
- `player_name`

These are convenience fields only. Commands should join the role dataset back to `player_game_stats` for the rest of the player/game context.

### Producer(s)

- `src/nbatools/commands/pipeline/pull_player_game_starter_roles.py`, a dedicated backfill command that fans out over `data/raw/games/{season}_{season_type_safe}.csv`
- the upstream NBA per-game box score endpoint `BoxScoreTraditionalV3.PlayerStats.position`
- any future compatibility layer that normalizes an alternate upstream source into this same contract

### Primary consumer(s)

- starter / bench execution for `player_game_summary`
- starter / bench execution for `player_game_finder`
- starter / bench execution for `season_leaders`
- future role-aware player routes that explicitly opt into the same contract

### Notes

This dataset is the authoritative starter / bench source for player-context natural-query execution.

Contract rules:

- `role_source` should identify the normalized upstream source, currently `boxscore_traditional_v3.position`
- `starter_flag` is derived from non-empty `starter_position_raw`
- rows may only be used for execution when `role_source_trusted=1`
- at minimum, trust requires exactly 5 starter-marked players in the row's `(game_id, team_id)` group
- if trust fails, `role_validation_reason` must explain why, such as `starter_count_not_five`
- if a requested role-filtered slice depends on even one row that is missing or
  untrusted in this dataset, commands must return `filter_not_supported` with
  the exact missing/untrusted player-game keys instead of partially filtering
  or fabricating bench assignments
- refreshed seasons treat this dataset as part of the required raw pipeline contract alongside `player_game_stats`

---


## 1A-availability. Official player-game participation and DNP observations

Conditional medical/health/status owners are separate from the primary query
subject. Complete subordinate owner/status spans are excluded only from primary
entity and operation selection; the full original question and requested status
reach the existing availability-status authorization guard. A Boston record stays
a Boston team record; a player comparison retains both primary players and its
existing combined display. Unsupported status conditions return qualified-data
unavailability before statistics execute, with no applied filters or answer.
Medical clearance, health, inactive/active status and absence reasons are not
inferred from played, DNP, box-score omission or current membership. This is
correctness containment; medical-state filtering remains unfinished and no new
status feed or public result schema is introduced. Ordinary played and unfiltered
consumers retain their existing source qualification and numerical semantics.
The same internal role proof covers adjective-before-owner status, coordinated
owners, and subordinate status/played predicate chains in either order. All
actors in a status-containing chain stay conditional; no partial played filter
is advertised as applied. Sports clearance for contact or practice remains an
unavailable medical condition. A requested team win count keeps its team-record
operation without treating AVAILABLE as evidence that the actor played. Broader
OR consumers remain unfinished and may retain their existing unsupported reason.

**Optional new additive dataset**:
`data/raw/player_game_availability/{season}_{season_type_safe}.csv`

- **Grain:** one player explicitly listed in one NBA game box score, identified by
  `(game_id, team_id, player_id)`; no rows are manufactured for
  unlisted players. Source team/game IDs are checked against the canonical
  finalized games catalog (two teams). The source's listed player rows are
  retained **before** starter-role filtering discards box-score nonplayers.
- **Fields:** `game_id, game_date, season, season_type, team_id, team_abbr,
  player_id, player_name, participation_state, source_minutes, source_comment,
  source, source_sha256, identity_source_sha256, coverage_scope`.
- **Producer:** `nbatools.commands.pipeline.pull_player_game_availability`
  supports **NBA Official Final Box PDFs** as targeted fallback/corroboration; these list playing,
  DNP/DND and inactive athletes with historical reasons. `--source report`
  validates PDF game date, visitor/home teams and both final scores against
  existing NBA game logs, plus unambiguous NBA player identities. PDFs are
  fetched from `statsdmz.nba.com/pdfs/YYYYMMDD/YYYYMMDD_AWAYHOME.pdf` with
  `pypdf`. For missing PDFs, official Stats `BoxScoreTraditionalV3.PlayerStats`,
  archived V3 JSON or `--source espn` can collect explicitly listed player
  observations. The ESPN and Stats options do not certify complete inactive
  lists, and are not automatic substitutes for official Final Box coverage. The ESPN adapter matches the exact game date, both teams, both
  final scores, home/away sides and completed status in both scoreboard and
  summary header, and resolves every reported athlete to a unique NBA player ID
  for that team/season; unresolved identities fail rather than substitute
  ESPN IDs for NBA IDs. ESPN rows keep the ESPN event ID in the `source` field.
  The separate importer does not refetch every core stat or modify the existing
  starter-role producer. Output uses resumable local checkpoint writes and
  atomic final CSV replacement. The module never publishes to R2 itself.
  Per-game `.imports.json` receipts bind the selected source and a normalized
  SHA256 of every saved player row. Resume requires matching rows and catalog
  scope; missing receipts, changed/truncated rows, and source switches trigger
  reacquisition. A full atomic `.partial.csv` preserves completed imports after
  interruption. These receipts verify local import integrity, not upstream
  authenticity, complete rosters, raw-response retention or R2 durability.
  The report adapter reads played names/minutes directly from scorer-report
  lines and requires their player IDs to match the canonical game's participant
  IDs; it never fills a missing PDF participant from local statistics. Original
  PDF bytes are retained under `data/raw/player_game_availability_sources/`
  by SHA256, with a report-reference JSON receipt recording URL, retrieval time,
  byte count and raw filename. Report rows carry `source_sha256` to bind them
  to those exact bytes even if a provider later revises a report. Other adapters
  currently leave that field empty and remain pending original-source retention.
  Offline replay uses `pipeline backfill-game-availability --source report
  --cached-reports <directory>`. The directory contains the report-reference
  receipt and its hash-named original PDF. Replay verifies exact URL, SHA256,
  size, timezone-qualified capture time and the same one-page NBA Final Box
  markers; it preserves original bytes and receipt time. Missing, altered or
  invalid inputs fail without network fallback. Unresolved identities also fail
  offline, rather than fetching CDN/profile sources or omitting listed rows.
  Cached reports cannot be combined with another source adapter.
  Cached Stats V3 replay accepts original `boxScoreTraditional.homeTeam` and
  `awayTeam` objects with `players[]`, not just legacy flattened `playerStats`
  archives. Side IDs must agree with the envelope; the downstream normalizer
  checks the requested game and canonical two-team set and rejects fractional,
  null or nonpositive IDs and duplicate players. Player `comment` and
  `statistics.minutes` retain explicit DNP versus unknown semantics. A missing
  minutes value alone remains unknown. Mixed nested/flattened populations are
  rejected. Every replay binds `source_sha256` to the original input bytes and
  explicitly supplied archives are re-read even on resume; an old import digest
  cannot hide a changed source. Preserve the original JSON with acquisition
  URL/parameters/capture-time metadata in the existing collection bundle.
  This is development staging: the V3 envelope supplies no independently checked
  game date/finality, the byte hash proves integrity rather than authenticity,
  and Stats rows remain ineligible for production publication/runtime filtering.
  It establishes listed same-game association, never tenure or unlisted absence.
  These files must accompany publication inputs. Identity lookup may use the
  immediately preceding season's canonical player/team IDs; that lookup never
  establishes current membership or absence without an explicit report row.
  Retained reports may explicitly select `--import-team-id <NBA team ID>`
  (repeatable). This validates both teams' headings, scores and inactive-list
  labels, then resolves every listed player of the selected teams. The import
  receipt binds `imported_team_ids` to the exact saved game rows and digest;
  absent scope retains the legacy both-team requirement. Publication validation
  accepts only a nonempty canonical subset matching that explicit receipt,
  with all existing original-source and identity checks. This changes no
  publication authorization. A scoped refresh rejects existing outside-scope
  rows without deleting them; complementary partial imports are not merged.
  A later full-game request must qualify both teams independently and cannot
  resume from one team's receipt. The default remains all-or-error. This permits
  Boston's unambiguous listed observations in the retained February 1, 2026
  report without assigning Milwaukee's ambiguous surname-only inactive entries.
  It establishes no tenure, other-game nonmembership or season-wide coverage.
  If no candidate exists, the official CDN game box score supplies identity only:
  exact game/date/finality, home/away teams and final scores must match first.
  Ambiguous IDs/names and canonical identity conflicts reject the import. CDN
  A CDN HTTP403 may instead use a unique NBA API static-catalog candidate to
  select an official NBA profile URL. The profile's retained HTML must confirm
  `PERSON_ID`, `FIRST_NAME`, `LAST_NAME` and `DISPLAY_FIRST_LAST` in its structured
  `props.pageProps.player.info`; the SDK catalog alone is not accepted evidence.
  Current profile team/status fields are ignored. A derived identity index binds
  each used profile's ID/name and original HTML hash; publication verifies all
  HTML receipts and canonical global-ID consistency. These HTML/index files stay
  alongside the report sources and must accompany permanent publication.
  An explicitly named inactive entry with empty parentheses (observed `Stevens ()`
  in the retained October26report) still establishes nonparticipation under the
  inactive heading; its medical/absence reason remains unknown. Original source
  clocks are retained: the October26Lakers displayed clocks sum to240:01 while the
  printed team total is240:00; no correction or false exact-time reconciliation
  is claimed. This does not change the game-specific DNP/points qualification.
  Source
  status/minutes do not determine output participation, and unlisted PDF players
  never become rows. `identity_source_sha256` binds any fallback to retained
  original JSON bytes and URL/time/hash/size receipts. Publication revalidates
  that JSON's game envelope and every row's ID/team/name mapping.
  Generation publication rejects availability overlays without valid import
  digests, canonical final-game/team scope, the exact away/home report reference,
  and matching retained PDF bytes/receipt. Temporary checkpoints, contradictory
  rows and sources without retained report provenance fail before any R2 write.
  The bounded official-report numerical test retains these actual source files
  and derived CSVs in the existing validation artifact; artifact staging is
  temporary and does not satisfy permanent R2 publication.
- **Structured archival producer:** `pipeline.structured_participation.stage_structured_game`
  qualifies retained Traditional V3 plus Summary V2 or V3 responses offline into
  this same dataset. Recommended scalable source is the structured combination;
  no per-game PDF prerequisite is introduced. Traditional supplies participant/DNP
  rows; Summary supplies explicit game-specific inactive identities and the final
  game/date/home-away/score envelope. An empty inactive array establishes no
  roster completeness. Every original response is retained by hash (2MB bound),
  with an archive revision, pinned source URL, retrieval timestamp and attribution.
  `source=nba_stats_structured_archive:<revision>:<game_id>` and `source_sha256`
  bind the exact composite `.structured.json` receipt and both original JSONs.
  Archive retrieval is not an original NBA capture or freshness timestamp.
  The bounded source is SportsDataverse hoopR's attributed NBA Stats raw archive,
  pinned to revision2e44b7c039f104bc6b41a1de494411e83a03714e (CC BY4.0).
  Qualification requires both teams, exact final/date/game identity, source and
  canonical team scores, complete agreement with canonical played identity/point
  rows, and no played/DNP/inactive conflicts. Known canonical name/ID contradictions
  reject for all listed players; exact given/family reversal is permitted for
  identities such as Yao Ming. Multiple broadcast summary records may differ in
  broadcaster only: all required game scope fields must agree. Explicit DNP rows
  cannot contain positive on-court activity counts. Original malformed durations
  (observed1997`29:60`) reject the game rather than being quietly normalized.
  Original comments, including legacy garbage suffixes, are opaque provenance,
  never qualified medical causes. Coverage stays `listed_player_rows_only`.
  Existing qualified rows cannot be dropped or contradicted by a replacement.
  Publication validation rebuilds the rows from retained originals and the
  canonical game, rejecting altered sources, packets or normalized rows. This
  prepares verifiable staging; it grants no production publication authority.
  Runtime consumes these qualified rows through existing observation/sample
  helpers. A season-wide query still needs known predicates across every candidate
  game. Same-game opposite-team association can disprove same-team absence;
  unlisted players and unrelated same-date games cannot establish nonmembership.
- **States:** `played` requires positive game minutes,
  `did_not_play` requires an explicit upstream
  DNP/DND/Inactive/Not-With-Team report and zero or missing minutes, and
  `unknown` covers ambiguous zero/absent minutes without
  an explicit nonparticipation statement. Contradictions are rejected.
- **Source truth:** NBA V3 `source_comment` is preserved verbatim; ESPN
  `didNotPlay=true` is retained only as an explicit DNP flag, never a claimed
  injury reason (ESPN generic reason text can also appear on played athletes).
  Both sources preserve their own `source` provenance. The ESPN summary
  `injuries` section is a **current-at-fetch** snapshot even when the requested
  `boxscore` is a historical game. It must never be used as historical
  injury/availability evidence for that game. Game-specific `didNotPlay` flags
  and documented NBA V3 comments are distinct from contemporary injury reports.
  For NBA V3, `source_comment` is preserved verbatim;
  do not transform coach decisions, illness, inactive and injuries into one
  injury statistic. `coverage_scope=listed_player_rows_only`
  establishes only positive source observations. Unlisted players might be
  outside the game-day roster OR omitted from the particular box-score source.
  The dataset alone **does not** certify a complete game-day roster,
  complete player/team tenure, or all missed games.
- **Consumer and promotion:** shared `filter_without_player` uses explicit
  report observations for each requested player across the complete candidate
  sample. `did_not_play` selects; `played` excludes. Missing or unknown
  observations, duplicate player/game identities, mismatched dates and ambiguous
  identities reject the answer rather than silently shrinking its denominator.
  Conjunctions qualify all players against the original candidate sample.
  Natural two-teammate clauses preserve the resolved pair and complete consumed
  span so later guards still inspect other clauses. Explicit out/not-playing/DNP
  suffixes select whole-game nonparticipation, never a medical reason; both-playing
  suffixes select positive-minute appearances. Numeric bounds on the primary
  subject remain independent predicates and displayed conditions name both players.
  Canonical positive-minute rows may additionally prove `played`, never absence.
  Shared `filter_with_player` requires positive numeric canonical minutes and
  same-team game identity; zero-minute rows and unresolved identities never
  turn a requested presence condition into an unfiltered sample. Team/player
  named-season splits select the named seasons before loading and qualifying
  participation, so excluded intermediate seasons are not part of the sample.
  A numerical condition attached to the teammate is not applied to the primary
  subject; that combined capability remains unfinished.
  Conflicting report/positive observations reject. Same-team predicates bind team IDs; an explicit opponent clause permits
  opposing-team observations, with ambiguous ownership for an individual player rejected.
  Team records with an explicit opponent also qualify `with_player` against
  that same game's subject/opponent team IDs and date, using the shared
  observation checks. This permits an opposing player's verified `played`
  predicate without treating that player as a teammate. Every game in the
  participation sample must have qualified evidence; explicit did-not-play observations can
  establish a genuine empty played sample. Missing, unknown, contradictory or
  ambiguous evidence remains unavailable. Without explicit matchup context,
  the existing played filter retains its same-team meaning. Neither path
  transfers membership to another game or establishes tenure or medical status.
  Natural explicit-matchup team records can retain two resolved played predicates
  joined by AND, while or a comma in the existing `with_player` conjunction.
  Each player independently binds the subject or opponent side; a pair can
  legitimately contain one player from each team. The full consumed clause is
  preserved for guards, and both names remain in applied filter metadata.
  Missing/unknown evidence for the second player cannot be hidden by an empty
  first predicate. This does not promote mixed played/absent, OR, player-owned
  numeric conditions, medical/status or on-court language.
  Explicit two-player played team records can distinguish original-window
  and qualifying last-N samples for a full-game, scalar-season matchup.
  `last_n_scope=original_window` selects and restricts the original matchup IDs
  after subject/opponent, venue and date context, then qualifies BOTH players
  across that entire selected window before remaining predicates. Older games
  outside that window need no participation qualification for this request;
  missing/unknown evidence inside it cannot be hidden by another false predicate.
  Explicit qualifying last-N and all legacy scopes (including unset/None,
  qualifying and window) retain participation-cohort-before-last-N ordering.
  Ordinary within/among/of-original-window and explicit qualifying forms preserve
  that distinction; unsupported routes/compositions do not inherit the new order.
  Bare new separate-clause temporal record requests remain contained.
  A bounded latest-original-one-matchup Boolean check ("did BOTH play?") selects
  the full canonical team row without a participation predicate, then qualifies
  both resolved names with the existing same-game identity/date checks inside
  protected execution. Both Yes and No retain that original game ID/date and
  team statistics. A No answer means at least one player did not play; it does
  not imply that neither played. Missing/unknown/contradictory facts or no
  original game cannot produce No. Metadata labels the predicates
  as played checks, not a matching `with_player` cohort on a false answer.
  This requires one explicit regular season, subject/opponent and exactly two
  PLAYED checks; playoff wording remains unfinished. Original selection can include home/road context or one explicit ISO
  date boundary. Latest-qualifying Boolean, N>1, mixed polarity, health/status,
  on-court, extra statistic and unread compositions remain unfinished.
  Scalar latest-original played checks use that same full canonical selection
  and qualified observation path at one-name arity. Explicit season/team/opponent
  context chooses the original matchup before participation, rather than the
  player's most recent appearance. Known played and explicit DNP yield Yes/No
  with the original team-game row; unknown/missing/conflicting facts yield an
  unavailable result without an older appearance substitute. A bare request's
  last-appearance team is only a candidate and needs qualified same-game subject
  membership; it is never certified as the current team from omission.
  Canonical `metadata.player` and identity-only `player_context` identify the
  checked target, while the finder row and caveat label totals as team evidence.
  No player row or zero box score is fabricated for DNP. Basic Yes stat details
  come only from a positive appearance matching the selected game/player/side/date.
  The old date/appearance-omission-to-No formatter has been removed. Scalar
  score/outcome yes-no semantics and legacy calendar/freshness interpretation
  are unchanged; qualifying/N>1, status/on-court and unread compositions stay open.
  One complete scalar minutes predicate on an explicit team/latest original
  named matchup in a regular season uses this same original TEAM-game selector
  and protected participation qualification. The checked player keeps identity-only
  metadata separately from the team table. Played athletes require a same-game,
  actual-side/date official report time: finite positive `source_minutes` whose
  seconds are integral within serialization tolerance. The answer shows MM:SS;
  rounded legacy player minutes never substitute for exact threshold evidence.
  The existing threshold-span extractor's optional `exact_stat` mode retains
  unshifted bounds and internal `min_inclusive`/`max_inclusive` flags in the
  existing yes/no note. Default legacy bound dictionaries/epsilon behavior are
  unchanged; no public request/result fields were added. Strict comparisons near
  a source second therefore keep their true inclusivity without epsilon guesses.
  Explicit DNP answers No to PLAYED plus any minutes bound (including upper
  bounds), because the player did not play, with no numericalzero/player row.
  Unknown/conflicting game-day facts or missing precise report time return
  `filter_not_supported` without a Boolean or older appearance substitute.
  Minutes-check labels describe checks on the retained game, not an applied
  player cohort; table totals remain team evidence. Native bare statistical
  minutes, multi-stat AND/OR/outcome checks outside this bounded original-matchup
  extension retain their tested accepted-main semantics. A bounded original-game
  conjunction also accepts one minutes predicate AND one distinct player count
  from the existing PTS/REB/AST/FG3M/STL/BLK/TOV vocabulary, including full
  HAVE/RECORD verbs, reversed order and a count range with its own inner AND.
  Both predicates retain their exact operator inclusivity; the shared extractor
  can apply its optional exact mode to a set of statistics without changing
  default dictionaries. Before comparing either played bound, the consumer
  requires exact report seconds AND a finite nonnegative integer count from
  the canonical row with that report's player/game/actual-side/date identity.
  A report-qualified 0:20 appearance remains played if canonical minutes round
  to0; a positive rounded MIN is not the participation requirement. Recorded
  count0 on a qualified appearance is real evidence; missing/null/fractional
  counts are unavailable even if the other predicate is false. Explicit DNP
  still means No to the conjunctive played check without inventing either zero.
  The original TEAM row remains separate from the checked-player identity;
  Minutes check and Count check labels preserve both requested predicates.
  The valid native bare MIN-first minutes-AND-HAVE/RECORD statistical check is restored
  only when its complete actor, predicates and scope are consumed. Reversed
  count-first native bare checks remain valid unfinished ordering cases. Broader
  original OR/grouped/outcome/extra-owner compositions remain unfinished;
  a legacy numerical note never authorizes an unread clause or older-row
  substitution. No all-AND language-completeness claim is made.
  Frozen source/consumer/precision contracts are under
  `tests/fixtures/qualified_original_minutes/` and
  `tests/fixtures/qualified_original_stat_pair/`.
  All 46 original PR462 absence obligations remain open. Baselines
  and exact original/qualifying source requirements are retained in
  `tests/fixtures/qualified_played_pair/temporal_obligations.json`; root-frozen
  preimplementation temporal controls are now retained as revealed regressions
  in `tests/fixtures/original_window_played_pair/revealed_controls.json`.
  Readers cache by immutable data generation and do not infer injury or on-court
  absence. Publication lineage is validated before activation. This consumer
  does not certify complete rosters, unlisted players, full-season coverage or
  permanent publication. Required broader positive queries stay unfinished until
  their entire requested samples have qualified source observations.
- **Backfill operation:**
  `nbatools-cli pipeline backfill-game-availability --season 2025-26 --source report --limit 3`
  pulls a bounded number of finalized NBA Official Final Box reports.
  NBA.com scorer PDFs were verified reachable from a GitHub-hosted runner, even
  though NBA Stats and CDN endpoints were not. The official PDF includes game
  date, team, scoring, DNP and inactive information, but the producer still
  refuses ambiguous player identities and unsupported seasons or missing data.
  `--cached-boxscores PATH` can instead read
  retained NBA Stats V3 boxscore JSON without external fetches. Existing
  pipeline publication/version checks and read-only runtime access remain unchanged.


## 1B. `player_game_period_stats`

### Path pattern

`data/raw/player_game_period_stats/{season}_{season_type_safe}.csv`

Examples:

- `data/raw/player_game_period_stats/2025-26_regular_season.csv`
- `data/raw/player_game_period_stats/2024-25_playoffs.csv`

### Grain

One row per **player-game period window** for the supported period semantics.

### Key fields

- `game_id`
- `player_id`
- `period_family`
- `period_value`

Recommended uniqueness expectation:

- unique on (`game_id`, `player_id`, `period_family`, `period_value`)

### Required columns

- `game_id`
- `season`
- `season_type`
- `game_date`
- `period_family`
- `period_value`
- `source_start_period`
- `source_end_period`
- `team_id`
- `team_abbr`
- `team_name`
- `opponent_team_id`
- `opponent_team_abbr`
- `opponent_team_name`
- `is_home`
- `is_away`
- `wl`
- `player_id`
- `player_name`
- `minutes`
- `pts`
- `fgm`
- `fga`
- `fg3m`
- `fg3a`
- `ftm`
- `fta`
- `oreb`
- `dreb`
- `reb`
- `ast`
- `stl`
- `blk`
- `tov`
- `pf`
- `plus_minus`

### Important derived/query fields

- `fg_pct`
- `fg3_pct`
- `ft_pct`
- `efg_pct`
- `ts_pct`
- `usg_pct`
- `ast_pct`
- `reb_pct`
- `tov_pct`
- `comment`

### Producer(s)

- `src/nbatools/commands/pipeline/pull_game_period_stats.py`, which fans out over
  `data/raw/games/{season}_{season_type_safe}.csv`
- `BoxScoreTraditionalV3` period-window requests for the traditional box-score totals
- `BoxScoreAdvancedV3` period-window requests for the player-only rate fields needed by
  `player_game_finder`

### Primary consumer(s)

- quarter / half / overtime execution on `player_game_finder`
- future player-context routes that explicitly opt into the same period-window contract

### Notes

This dataset is the authoritative period-window source for the initial player route boundary.

Contract rules:

- `BoxScoreTraditionalV3` is the source of record for player-grain period windows and owns
  the traditional box-score columns in this table
- `BoxScoreAdvancedV3` is an explicit player-only enrichment path for `usg_pct`, `ast_pct`,
  `reb_pct`, and `tov_pct`; the initial team route boundary does not depend on AdvancedV3
- supported period semantics are represented as explicit `period_family` / `period_value`
  pairs:
  - `quarter` with values `1`, `2`, `3`, `4`
  - `half` with values `first`, `second`
  - `overtime` with value `OT`
- `source_start_period` / `source_end_period` record the exact upstream window used to
  materialize the row:
  - quarters: `1-1`, `2-2`, `3-3`, `4-4`
  - halves: `1-2`, `3-4`
  - overtime: `5-14`, aggregated into one `OT` row only when the returned window shows real
    overtime activity
- upstream box-score requests use `RangeType=1`, `StartRange=0`, and
  `EndRange=28800`; `RangeType=0` returns full-game totals even when period
  bounds are supplied and is not valid for this dataset
- validation rejects player minutes above 12.5 for a quarter or 24.5 for a
  half, preventing full-game rows from being mislabeled as period windows
- the upstream period response may omit a whole-game participant who logged
  zero minutes in a selected quarter or half; the producer materializes that
  authoritative absence as a zero-stat row for the required player-game/window
  key so exact coverage does not confuse non-participation with missing data
- zero completion applies only to the six standard quarter/half windows;
  overtime rows are never invented for games or players without OT activity
- this contract is period-only; it does not define `clutch`, and no consumer may treat these
  rows as a clutch-capable substitute
- commands must compare the requested base entity-game key set with this
  dataset's exact requested window; one missing key returns
  `filter_not_supported` with the missing game/entity/window detail instead of
  partially mixing whole-game and period-window rows

---

## 1C. `play_by_play_events` and derived clutch stats

The approved source path for clutch execution is official `PlayByPlayV3` event
data plus local score-state derivation. This section is the durable source
boundary.

Setup-only cloud development staging additionally supports a qualified archived
official CDN feed as `pbp_source=cdn.nba.com.liveData.playbyplay`, with
`pbp_source_schema_version=cdn_live_pbp.v1`. This is a distinct source, not NBA
Stats V3. `source_order_number` preserves the CDN's original `orderNumber` as
chronology; `action_number` preserves original `actionNumber` as event identity.
Delayed supplemental records can have a later identity but an earlier timeline
position. Ingestion, whole-game trust, loading and existing score-state consumers
use the source timeline, without dropping or renumbering events. CDN rows require
unique positive integral order values, one source/schema per game, forward periods,
nonincreasing within-period clocks and nondecreasing scores; legacy Stats ordering
and all existing terminal score/period gates remain intact.

`tools/cloud_cdn_archive.py` retrieves one fixed game (`0022500003`) from an
authenticated, pinned public archive; preserves the exact original selected CSV
records, original archive checksum, Apache-2.0 attribution and source receipt;
and writes a new staging directory. The bounded evidence is 605 events, ending
NYK119–CLE111 in period4. Its scoped versioned receipt and nine-file immutable
candidate validate an **isolated development subset**, not a complete season or
registered production R2 package. No current freshness, NBA Stats equivalence,
period/on-off replacement or new clutch-feature acceptance follows. All production
source/base/registration/approval gates remain separate.

The raw `play_by_play_events` dataset path, validation, and loader exist. The
processed `player_game_clutch_stats` and `team_game_clutch_stats` derivation
paths, validation, loaders, and coverage-gated route execution also exist for
`player_game_summary`, `player_game_finder`, `team_record`, and
`season_leaders`.

### Raw path

`data/raw/play_by_play_events/{season}_{season_type_safe}.csv`

### Raw grain

One row per NBA play-by-play event.

### Raw key fields

- `season`
- `season_type`
- `game_id`
- `action_number`

### Raw required columns

- `season`
- `season_type`
- `game_id`
- `action_number`
- `period`
- `clock`
- `clock_seconds_remaining`
- `team_id`
- `team_abbr`
- `player_id`
- `player_name`
- `action_type`
- `sub_type`
- `description`
- `score_home`
- `score_away`
- `pbp_source`
- `pbp_source_trusted`
- `pbp_validation_reason`

### Derived paths

- `data/processed/player_game_clutch_stats/{season}_{season_type_safe}.csv`,
  at one row per player-game clutch sample keyed by `season`, `season_type`,
  `game_id`, `team_id`, and `player_id`
- `data/processed/team_game_clutch_stats/{season}_{season_type_safe}.csv`, at
  one row per team-game clutch sample keyed by `season`, `season_type`,
  `game_id`, and `team_id`

Derived clutch rows include `clutch_window`,
`clutch_time_remaining_start`, `clutch_score_margin_max`, `clutch_events`,
`clutch_seconds`, event-derived `pts`, `clutch_source`,
`clutch_source_trusted`, and `clutch_validation_reason`.

Contract rules:

- clutch means last five minutes of the fourth quarter or overtime with the
  score within five points
- raw play-by-play rows must have parseable clocks, parseable home/away score
  state, unique event keys, and trusted event ordering
- normalization alone leaves rows untrusted; a game becomes trusted only after
  the validator reconciles it with an expected game and the paired whole-game
  team final scores
- trusted play-by-play coverage must contain every expected base game, and each
  game's final action must reach `clock_seconds_remaining=0`, the expected
  regulation/overtime period, and the same unordered final-score pair as
  `team_game_stats`
- missing games, truncated terminal actions, terminal-period drift, or final
  score disagreement must remain explicitly missing/untrusted; row-local
  `pbp_source_trusted=1` values are recomputed and cannot override these checks
- whole-game logs and period-only box-score windows must not be used as clutch
  substitutes
- route execution may only use derived clutch rows when source trust and
  score-state validation pass for the requested slice
- raw play-by-play must cover every requested base game before derived clutch
  rows may execute
- every qualifying play-by-play entity-game key must have a trusted derived row
  for the exact `clutch_window=1`, `clutch_time_remaining_start=300`, and
  `clutch_score_margin_max=5` window
- one missing/untrusted PBP game or derived clutch key returns
  `filter_not_supported` with exact coverage detail rather than partial results
- rate and efficiency metrics may only ship after their sample denominators are
  validated against the play-by-play derivation

`clutch_seconds` is the span between the maximum and minimum qualifying event
clock values for that entity-game sample. It is an event-window span, not
player time-on-court or possession time, and must not be labeled as either.

---

## 1D. `team_player_on_off_summary`

The approved source for `player_on_off` execution is the upstream
`teamplayeronoffsummary` split table, called through
`nba_api.stats.endpoints.TeamPlayerOnOffSummary`. This section is the durable
source boundary.

This section defines the approved raw source dataset for `player_on_off`
execution. The route may only use rows when validation marks the requested
single-player slice trusted; missing or untrusted coverage keeps the explicit
unsupported/no-result response.

### Path pattern

`data/raw/team_player_on_off_summary/{season}_{season_type_safe}.csv`

Examples:

- `data/raw/team_player_on_off_summary/2025-26_regular_season.csv`
- `data/raw/team_player_on_off_summary/2024-25_playoffs.csv`

### Grain

One row per **team / queried player / presence-state season split**.

The upstream source exposes separate on-court and off-court row groups. The
normalized dataset should combine them into one table with explicit
`presence_state` values.

### Key fields

- `season`
- `season_type`
- `team_id`
- `player_id`
- `presence_state`

Recommended uniqueness expectation:

- unique on (`season`, `season_type`, `team_id`, `player_id`, `presence_state`)

### Required columns

- `season`
- `season_type`
- `team_id`
- `team_abbr`
- `team_name`
- `player_id`
- `player_name`
- `presence_state`
- `court_status_raw`
- `gp`
- `minutes`
- `plus_minus`
- `off_rating`
- `def_rating`
- `net_rating`
- `source_endpoint`
- `source_pull_date`
- `source_schema_version`
- `coverage_trusted`
- `coverage_validation_reason`

### Producer(s)

- `src/nbatools/commands/pipeline/pull_team_player_on_off_summary.py`,
  wrapping
  `nba_api.stats.endpoints.TeamPlayerOnOffSummary`
- any future compatibility layer that normalizes an alternate upstream on/off
  split source into this same contract

### Primary consumer(s)

- coverage-gated `player_on_off` execution

### Notes

Contract rules:

- `PlayersOnCourtTeamPlayerOnOffSummary` rows should normalize to
  `presence_state=on`
- `PlayersOffCourtTeamPlayerOnOffSummary` rows should normalize to
  `presence_state=off`
- source `VS_PLAYER_ID` / `VS_PLAYER_NAME` should normalize to `player_id` /
  `player_name`
- possessions are not exposed by the approved minimum source; route execution
  should use `minutes` and `gp` as the sample-size fields unless a later
  approved source adds possessions
- route execution may only use rows when both `on` and `off` states exist for
  the requested player/team/season slice and `coverage_trusted=1`
- missing or untrusted coverage must keep the existing honest unsupported-data
  response instead of fabricating or partially filtering on/off splits
- whole-game `without_player` absence remains a separate team/game-log filter
  and must not be treated as on/off execution

---

## 1E. `league_lineup_viz`

The approved source path for `lineup_summary` and `lineup_leaderboard`
execution is the upstream `leaguelineupviz` lineup-unit table, called through
`nba_api.stats.endpoints.LeagueLineupViz`. This section is the durable source
boundary.

This raw source dataset path, validation, loader, and coverage-gated route
execution exist. Missing or untrusted coverage returns an explicit
unsupported/no-result response.

### Path pattern

`data/raw/league_lineup_viz/{season}_{season_type_safe}.csv`

Examples:

- `data/raw/league_lineup_viz/2025-26_regular_season.csv`
- `data/raw/league_lineup_viz/2024-25_playoffs.csv`

### Grain

One row per **team lineup unit / unit size / minimum-minute threshold season
split**.

### Key fields

- `season`
- `season_type`
- `team_id`
- `unit_size`
- `lineup_id`
- `minute_minimum`

Recommended uniqueness expectation:

- unique on (`season`, `season_type`, `team_id`, `unit_size`, `lineup_id`,
  `minute_minimum`)

### Required columns

- `season`
- `season_type`
- `team_id`
- `team_abbr`
- `unit_size`
- `lineup_id`
- `lineup_name`
- `player_ids`
- `player_names`
- `minute_minimum`
- `minutes`
- `off_rating`
- `def_rating`
- `net_rating`
- `pace`
- `ts_pct`
- `source_endpoint`
- `source_pull_date`
- `source_schema_version`
- `coverage_trusted`
- `coverage_validation_reason`

### Important derived/query fields

- `player_ids` should be a normalized, deterministic membership list parsed
  from source `GROUP_ID`
- `player_names` should be a normalized membership list parsed from source
  `GROUP_NAME`
- `lineup_id` should preserve the stable source membership key so specific
  lineup queries and leaderboard rows agree

### Producer(s)

- `src/nbatools/commands/pipeline/pull_league_lineup_viz.py`, wrapping
  `nba_api.stats.endpoints.LeagueLineupViz`
- any future compatibility layer that normalizes an alternate upstream
  lineup-unit source into this same contract

### Primary consumer(s)

- `lineup_summary` execution
- `lineup_leaderboard` execution

### Notes

Contract rules:

- source `GROUP_ID` / `GROUP_NAME` are the lineup membership source of record
- source `MinutesMin` should normalize to `minute_minimum`
- route execution may only use rows when the parsed membership count matches
  `unit_size` and `coverage_trusted=1`
- possessions and games represented are not exposed by the approved minimum
  source; route execution should use `minutes` as the sample-size field unless a
  later approved enrichment source adds possessions or games
- missing or untrusted coverage must keep the existing honest unsupported-data
  response instead of fabricating or partially filtering lineup-unit results
- roster membership remains an identity/enrichment source only and must not be
  treated as lineup-unit execution

---

## 2. `team_game_stats`

### Path pattern

`data/raw/team_game_stats/{season}_{season_type_safe}.csv`

Examples:

- `data/raw/team_game_stats/2025-26_regular_season.csv`
- `data/raw/team_game_stats/2024-25_playoffs.csv`

### Grain

One row per **team-game**.

### Key fields

- `game_id`
- `team_id`

Recommended uniqueness expectation:

- unique on (`game_id`, `team_id`)

### Required columns

- `game_id`
- `game_date`
- `season`
- `season_type`
- `team_id`
- `team_abbr`
- `team_name`
- `opponent_team_abbr`
- `matchup`
- `wl`
- `pts`
- `reb`
- `ast`
- `stl`
- `blk`
- `tov`
- `fgm`
- `fga`
- `fg3m`
- `fg3a`
- `ftm`
- `fta`
- `plus_minus`

### Important derived/query fields

- `is_home`
- `is_away`
- `fg_pct`
- `fg3_pct`
- `ft_pct`
- `efg_pct`
- `ts_pct`

### Producer(s)

- raw ingestion commands that pull team game logs from the NBA data source
- any cleanup/standardization layer that normalizes the raw pull into this contract

### Primary consumer(s)

- `game_finder`
- `game_summary`
- `team_compare`
- `team_split_summary`
- `team_streak_finder`
- natural-query team finder/summary/comparison/split/streak routes
- grouped boolean execution over team game samples

### Notes

This is the core team query dataset. Team summary, split, and streak behaviors should be designed around this contract.

Each game must have exactly two reciprocal participant rows. Their team and
opponent identities must agree with each other and with the canonical `games`
participants. Final `wl` is derived from the paired points, and canonical team
`plus_minus` is exactly `pts - opponent_pts`; paired plus-minus values must be
opposites. The ingestion normalizer replaces upstream fractional or otherwise
inconsistent team `PLUS_MINUS` values with this score-derived value, while raw
validation rejects any stored score/WL/plus-minus/identity drift.

Trusted standard-site games have exactly one home and one away row matching the
canonical designation.

For a neutral game whose canonical `games` row has no trusted home/away
designation, both participant rows use `is_home=0` and `is_away=0`. This keeps
neutral games in whole-game samples without inventing venue roles or presenting
two away teams.

---

## 2A. `team_game_period_stats`

### Path pattern

`data/raw/team_game_period_stats/{season}_{season_type_safe}.csv`

Examples:

- `data/raw/team_game_period_stats/2025-26_regular_season.csv`
- `data/raw/team_game_period_stats/2024-25_playoffs.csv`

### Grain

One row per **team-game period window** for the supported period semantics.

### Key fields

- `game_id`
- `team_id`
- `period_family`
- `period_value`

Recommended uniqueness expectation:

- unique on (`game_id`, `team_id`, `period_family`, `period_value`)

### Required columns

- `game_id`
- `season`
- `season_type`
- `game_date`
- `period_family`
- `period_value`
- `source_start_period`
- `source_end_period`
- `team_id`
- `team_abbr`
- `team_name`
- `opponent_team_id`
- `opponent_team_abbr`
- `opponent_team_name`
- `is_home`
- `is_away`
- `wl`
- `minutes`
- `pts`
- `fgm`
- `fga`
- `fg3m`
- `fg3a`
- `ftm`
- `fta`
- `oreb`
- `dreb`
- `reb`
- `ast`
- `stl`
- `blk`
- `tov`
- `pf`
- `plus_minus`

### Important derived/query fields

- `fg_pct`
- `fg3_pct`
- `ft_pct`
- `efg_pct`
- `ts_pct`

### Producer(s)

- `src/nbatools/commands/pipeline/pull_game_period_stats.py`, which fans out over
  `data/raw/games/{season}_{season_type_safe}.csv`
- `BoxScoreTraditionalV3` period-window requests for the team-grain period totals

### Primary consumer(s)

- quarter / half / overtime execution on `team_record`
- future team-context routes that explicitly opt into the same period-window contract

### Notes

This dataset is the authoritative period-window source for the initial team route boundary.

Contract rules:

- `BoxScoreTraditionalV3` is the source of record for team-grain period windows
- supported period semantics are represented with the same `period_family` / `period_value`
  vocabulary as `player_game_period_stats`
- team window validation rejects more than 75 team minutes for a quarter or
  150 for a half, preventing full-game totals from passing as period data
- exact overtime coverage compares period rows only with whole-game team rows
  whose team minutes prove that the game reached overtime; regulation games do
  not require fabricated OT rows
- `wl` is a period-window outcome derived from the period point differential:
  `W` when `plus_minus > 0`, `L` when `plus_minus < 0`, and `T` when the selected period
  ends tied
- `team_record` owns the downstream handling of `T`; the raw dataset must preserve that state
  instead of collapsing tied period windows into whole-game semantics
- this contract is period-only; it does not power `clutch`
- commands must compare the requested base team-game key set with this
  dataset's exact requested window; one missing key returns
  `filter_not_supported` with the missing game/team/window detail instead of
  partially mixing whole-game and period-window rows

---

## 2B. `team_conference_membership`

### Path pattern

`data/raw/teams/team_conference_membership.csv`

### Grain

One row per **season-team**.

### Key fields

- `season`
- `team_abbr`

Recommended uniqueness expectation:

- unique on (`season`, `team_abbr`)

### Required columns

- `season`
- `team_abbr`
- `team_id`
- `conference`
- `division`
- `source`
- `coverage_trusted`

### Current trusted coverage

- `2024-25`
- `2025-26`

Each trusted season must validate to exactly 30 teams, exactly 15 East teams,
exactly 15 West teams, and exactly five teams in each NBA division.

### Field rules

- `conference` must be exactly `East` or `West`
- `coverage_trusted` must be a stable boolean/0-1 value
- `source` must identify the source decision for the row
- `division` must be one of `Atlantic`, `Central`, `Southeast`, `Northwest`,
  `Pacific`, or `Southwest`
- `team_id` is required for the current trusted rows and must match the
  corresponding `team_game_stats` identity for the same season

### Producer(s)

- manual curation for the current rows, recorded as
  `manual_current_nba_alignment_2026-05-17`
- any future source refresh or historical expansion must preserve this same
  grain and trust contract

### Primary consumer(s)

- `team_record` opponent-conference filters for trusted current-era seasons
  (`2024-25`, `2025-26`)
- `team_record` and `team_record_leaderboard` opponent-division filters for
  trusted current-era regular seasons (`2024-25`, `2025-26`)
- data validation tests for membership coverage and game-log abbreviation
  consistency

### Validation rules

For each trusted season:

- no duplicate (`season`, `team_abbr`) rows
- no null or blank `conference`
- `conference` values are only `East` and `West`
- exactly 30 trusted teams
- exactly 15 East and 15 West teams
- every trusted `team_abbr` appears in
  `data/raw/team_game_stats/{season}_regular_season.csv`
- every team abbreviation in the matching `team_game_stats` season file has a
  trusted conference membership row
- included `division` values are non-empty and balanced to five teams per NBA
  division for the current trusted seasons

### Notes

Do not infer conference membership from standings rank ordering. Do not use the
incomplete `teams_reference.csv` file as the source of truth for this contract.

Missing or untrusted conference coverage keeps opponent-conference query
behavior unsupported/no-result. Missing or untrusted division coverage keeps
opponent-division query behavior unsupported/no-result. Neither condition may
broaden into an unfiltered full-season team record. Geography phrases such as
`east coast teams`, mixed conference-plus-division wording, and playoff
division record wording remain outside this contract.

---

## 3. `player_season_advanced`

### Path pattern

`data/raw/player_season_advanced/{season}_{season_type_safe}.csv`

### Grain

One row per **player-season**.

### Key fields

- `season`
- `season_type`
- `player_id`
- `team_id`

### Required columns

At minimum, commands depending on this table should expect:

- `player_id`
- `player_name`
- `team_id`
- `games_played`

### Common advanced columns

Depending on source availability, this dataset may include:

- `minutes_per_game`
- `pts_per_game`
- `reb_per_game`
- `ast_per_game`
- `fg_pct`
- `fg3_pct`
- `ft_pct`
- `usage_rate`
- `ts_pct`
- `pie`
- `off_rating`
- `def_rating`
- `net_rating`

### Producer(s)

- raw player season advanced pull commands

### Primary consumer(s)

- `season_leaders`
- any future player season leaderboard or leaderboard-adjacent queries

### Notes

If a requested season leaderboard stat is not directly present here, the command may fall back to building it from `player_game_stats`. That fallback behavior should stay explicit and tested.

---

## 4. `team_season_advanced`

### Path pattern

`data/raw/team_season_advanced/{season}_{season_type_safe}.csv`

### Grain

One row per **team-season**.

### Key fields

- `season`
- `season_type`
- `team_id`

### Required columns

At minimum, commands depending on this table should expect:

- `team_id`
- `team_abbr`
- `team_name`
- `games_played`

### Common advanced columns

Depending on source availability, this dataset may include:

- `pts_per_game`
- `reb_per_game`
- `ast_per_game`
- `fg3m_per_game`
- `efg_pct`
- `ts_pct`
- `off_rating`
- `def_rating`
- `net_rating`
- `pace`

### Producer(s)

- raw team season advanced pull commands

### Primary consumer(s)

- `season_team_leaders`
- natural team leaderboard queries
- future team season ranking features

### Notes

If date-windowed leaderboard behavior needs per-window recomputation, the command may need to derive results from `team_game_stats` instead of directly trusting full-season advanced rows.

---

## 5. `rosters`

### Path pattern

`data/raw/rosters/{season}.csv`

### Grain

Typically one row per **player-team-season roster entry**.

### Key fields

- `season`
- `player_id`
- `team_id`

### Required columns

- `player_id`
- `player_name`
- `team_id`
- `team_abbr`

### Producer(s)

- raw roster pull commands

### Primary consumer(s)

- season leaderboard enrichment when `team_abbr` is missing from season advanced datasets
- `player_game_finder` season-specific position and rookie population filters

### Notes

This dataset is primarily used as an enrichment table, not a primary query surface.
`CommonTeamRoster` is a season/team roster snapshot source, not an authoritative
ledger of every historical player-team game appearance. Receipt validation
therefore enforces this table's schema, grain, slice labels, and checksum, but
does not claim exact coverage of all `player_game_stats` player-team keys.
Role and period execution use their dedicated exact player-game coverage
contracts instead.

For `player_game_finder` classification, each requested season file must contain
rows for that season and `season` / `player_id`, plus `position` for a position
filter and `experience_years` for a rookie filter. Position codes use the existing
position-group mapping; rookie means a numeric experience value of zero.
Experience values must be nonnegative whole numbers. Missing, blank or invalid
requested values are unknown classifications, not evidence that a player is
outside the population. Unrequested classification fields are not required.

The join is by (`season`, `player_id`), retaining the player-game grain. A player
listed under multiple team snapshots qualifies when a complete requested
classification matches in at least one entry. An unknown entry alongside only
nonmatching entries does not prove exclusion. These snapshot classifications do
not establish game-date membership, injury status or on-court presence.

When some candidate games cannot be classified, a nonempty result identifies
itself in its result caveats as an **incomplete population**: the ranking covers
the known classified subset and states the omitted game count. Its table also
carries `population_scope` so text/CSV exports retain that limitation. It is not
an exhaustive league ranking. If no qualifying games can be verified while
unknown candidates remain, the response reports unavailable classification rather
than a verified `no_match`. Missing, empty, wrong-season or required-column-less
season files are unavailable; another season's rows cannot supply that coverage.
Complete-population ranking remains unfinished wherever the snapshot lacks these
classifications; unavailable-data containment is not numerical acceptance.

---

## 6. Processed feature tables

The repo now includes processing/build command groups. As processed feature tables become required dependencies for query behavior, each one should be documented here with the same structure as above.

Likely candidates include:

- player game feature tables
- team game feature tables
- game-level combined feature tables
- league season stats tables
- standings snapshot derivatives

### Current rule

A processed table should be added to this document once either of the following becomes true:

- a query command depends on it directly
- multiple commands depend on it indirectly and a contract is needed to stabilize future work

---

## 6A. `schedule_context_features`

### Path pattern

`data/processed/schedule_context_features/{season}_{season_type_safe}.csv`

Examples:

- `data/processed/schedule_context_features/2025-26_regular_season.csv`
- `data/processed/schedule_context_features/2024-25_playoffs.csv`

### Grain

One row per **team-game**.

### Key fields

- `game_id`
- `team_id`

Recommended uniqueness expectation:

- unique on (`game_id`, `team_id`)

### Required columns

- `game_id`
- `season`
- `season_type`
- `game_date`
- `team_id`
- `team_abbr`
- `team_name`
- `opponent_team_id`
- `opponent_team_abbr`
- `opponent_team_name`
- `is_home`
- `is_away`
- `rest_days`
- `opponent_rest_days`
- `back_to_back`
- `rest_advantage`
- `score_margin`
- `one_possession`
- `nationally_televised`
- `national_tv_source`
- `national_tv_source_trusted`
- `schedule_context_source`
- `schedule_context_source_trusted`

### Important derived/query fields

- `rest_days` is normalized to full off days since the team's previous game;
  the second game of a back-to-back has `rest_days=0`.
- `back_to_back` is `1` only when the previous team game was the previous
  calendar day.
- `rest_advantage` is one of `advantage`, `disadvantage`, `even`, or `unknown`
  relative to the opponent's normalized rest for the same game.
- `one_possession` is `1` when the final absolute scoring margin is `<= 3`;
  `score_margin` comes from the two teams' points, not the stored plus-minus.
- `nationally_televised` is `1` only when the schedule source carries a
  non-empty national-TV marker.

### Producer(s)

- `src/nbatools/commands/pipeline/build_schedule_context_features.py`
- inputs: `team_game_stats` plus `schedule`

### Primary consumer(s)

- schedule-context execution on `team_record`
- schedule-context execution on `player_game_summary`

### Notes

This is the execution-grade owner for whole-game schedule-context filters in the
initial Phase H route boundary.

Contract rules:

- command owners must join by (`game_id`, `team_id`) so team-relative rest and
  back-to-back state is not confused with game-level state
- missing, empty, incomplete, or untrusted schedule-context coverage must fail
  closed. The player-summary and team-record command owners translate the
  coverage note from `apply_schedule_context_filters()` into a structured
  `NoResult` with `result_reason="filter_not_supported"`; they must never return
  the original unfiltered game set as the requested answer
- `national_tv_source_trusted=0` means the raw schedule source is still acting
  as the historical placeholder. Commands may execute other trusted
  schedule-context filters, but a requested `nationally_televised` filter must
  fail closed with `result_reason="filter_not_supported"`
- current raw `pull_schedule` output can still produce blank `national_tv`
  values; a season file is considered national-TV trusted only when at least
  one non-empty national-TV marker is present

---

## 7. Sample-aware metric contract

Player sample-aware advanced metrics currently include:

- `usg_pct`
- `ast_pct`
- `reb_pct`

### Contract expectation

These metrics are not generic season lookups. They must be computed from the filtered player-game sample plus the required supporting season/team context used by the implementation.

### Where they should appear

These metrics may appear in:

- player summaries
- player comparisons
- player split summaries
- pretty output
- raw structured output

### Rule

If the sample changes, these metrics must reflect the sample.

Do not silently substitute season-average values for filtered-sample outputs.

---

## 8. Dataset validation receipt contract

Each season/type slice has an authoritative, versioned validation receipt at:

`data/metadata/dataset_manifests/<season>_<season_type>.json`

Schema version 1 binds every applicable dataset record to one receipt
`generation_id`. Each record declares its lifecycle layer, source, grain, key
columns, required schema columns, row count, file SHA-256, key-set SHA-256,
expected/observed coverage,
trust result, and validation state. A receipt is `passed` only when all required
files are present and readable, their keys match the required cross-dataset
game/entity sets, required period windows are covered, trust fields pass, and
every dataset record names the receipt generation.

Optional capability datasets are recorded as `unavailable` when absent. That
does not fail the base slice. Once an optional dataset is present, however, a
corrupt file, incomplete key set, or failed trust marker fails the whole
receipt; presence must never be promoted as trustworthy capability coverage.

Receipt inspection recomputes current file checksums. A corrupt receipt,
generation mismatch, checksum drift, missing required file, incomplete key or
window set, or present-but-untrusted optional dataset is a failed validation
state. `backfill_manifest.csv` remains a compatibility index, but file
existence or a legacy completeness bit is not authoritative validation.

Receipt creation is the final validation step after raw validation and
processed builds. It does not rebuild, refresh, upload, or promote datasets.

### Runtime generation-selection contract

Validation-receipt generation IDs describe one season/type slice. Runtime
publication uses a separate active generation that identifies a coherent
whole-data snapshot. The active pointer is a JSON object at
`data/metadata/active_generation.json` for local data or
`metadata/active_generation.json` in R2:

```json
{"generation_id": "<immutable-generation-id>"}
```

When the pointer is present, every logical runtime path is resolved beneath
`data/generations/<generation_id>/` locally or
`generations/<generation_id>/` in R2. The generation ID may contain letters,
digits, `.`, `_`, and `-`; path separators are rejected. A missing pointer
selects legacy canonical paths so existing unpublished local data remains
readable. A malformed or unreadable pointer is an error and must not fall back
to a potentially mixed snapshot.

Natural and structured query entry points pin the selected generation for the
entire request. File downloads, DataFrame loader caches, query-result identity
lookups, and parser entity indexes all include that pinned source generation
in their cache identity. A pointer switch affects only later requests; an
in-flight request continues reading its original immutable directory or
prefix.

### Generation publication contract

The canonical `data/` tree is a staging workspace, not a live mutable runtime
snapshot. Publication copies its non-hidden files into an immutable generation
and writes `metadata/generation_manifest.json` inside that generation. The
manifest binds the runtime generation ID to the exact relative path, byte size,
and SHA-256 of every staged file. Publication refuses an empty snapshot,
symlinks, unsafe paths, a missing/failed dataset validation receipt, receipt
generation mismatch, missing manifested data, or any checksum mismatch.

Local generations are staged on the same filesystem beneath
`data/generations/.staging-*`, validated, and atomically renamed to
`data/generations/<generation_id>/`. R2 generations are uploaded beneath
`generations/<generation_id>/`; every object is verified by byte length and
`nbatools-sha256` metadata. An existing generation ID is reusable only when
its immutable content matches exactly. A collision with different content
fails closed.

Only after the complete generation validates does publication switch
`metadata/active_generation.json`. Local switching uses an atomic file replace
with compare-and-swap ownership of the prior pointer. R2 switching is a single
conditional object write using the prior pointer ETag (or an absent-object
precondition for the first publication). Concurrent publishers therefore
cannot silently overwrite each other. A partial copy/upload or failed pointer
write leaves the prior generation active; inactive immutable files may remain
for an idempotent retry but cannot become runtime-visible.

The pointer retains `previous_generation_id`, `manifest_sha256`, and
`published_at` in addition to the runtime-required `generation_id`. The
rollback command first validates that retained target, then conditionally
switches the same pointer and retains the generation it rolled back from.
Readers already pinned to either generation remain coherent throughout a
publish or rollback.

Before the first R2 migration, publish the current last-good snapshot as a
baseline generation before staging a new candidate. Automated R2 rollback to
the unmanifested `legacy` namespace is refused; after bootstrap, every rollback
target is immutable and manifest-verified. Local legacy rollback remains
available only when the canonical dataset receipts still validate.

`pipeline publish-generation` is the only repository-supported mutable data
publication path. Direct canonical-key writes through `pipeline sync-r2` are
disabled; `sync-r2 --dry-run` remains read-only legacy-difference diagnostics.
These publication rules do not change the per-slice validation receipt
contract above.

## 9. Command-to-dataset mapping summary

### Player query surface

- `player_game_finder` -> `player_game_stats`, or `player_game_period_stats` when a supported quarter / half / OT filter is execution-backed for the requested slice
- `player_game_summary` -> `player_game_stats` + supporting advanced metric context, plus `schedule_context_features` for supported schedule-context filters
- `player_compare` -> `player_game_stats` + supporting advanced metric context
- `player_split_summary` -> `player_game_stats` + supporting advanced metric context
- `player_streak_finder` -> `player_game_stats`
- `season_leaders` -> `player_season_advanced` and/or `player_game_stats`, plus `rosters` for enrichment

### Team query surface

- `game_finder` -> `team_game_stats`
- `game_summary` -> `team_game_stats`
- `team_compare` -> `team_game_stats`
- `team_record` -> `team_game_stats`, or `team_game_period_stats` when a supported quarter / half / OT filter is execution-backed for the requested slice, plus `schedule_context_features` for supported schedule-context filters
- `team_split_summary` -> `team_game_stats`
- `team_streak_finder` -> `team_game_stats`
- `season_team_leaders` -> `team_season_advanced` and/or `team_game_stats`

---

## 10. Future expectations

As the repo evolves toward a UI-based search app, these data contracts should help preserve:

- stable engine behavior
- predictable query semantics
- cleaner agent contributions
- easier refactors
- clearer migration paths if storage evolves beyond CSV

When adding a new core dataset, add it here before making it an implicit dependency.

### Source-backed boundaries

- `clutch` uses official `PlayByPlayV3` plus local score-state derivation. The
  raw `play_by_play_events` dataset path and processed
  `player_game_clutch_stats` / `team_game_clutch_stats` derivations exist with
  validation, loaders, and exact coverage-gated route execution. Missing or
  untrusted PBP/clutch keys return `filter_not_supported` with exact game/key
  detail. Whole-game logs and
  period-only box-score windows remain rejected as clutch substitutes.
- `player_on_off` uses the approved upstream source path:
  `teamplayeronoffsummary` via
  `nba_api.stats.endpoints.TeamPlayerOnOffSummary`. The source dataset path,
  validation, loader, and coverage-gated `player_on_off` execution exist.
  Missing or untrusted coverage keeps the explicit unsupported-data response.
  Whole-game `without_player` absence remains rejected as an on/off substitute
  because it has no on-court/off-court sample boundary.
- `lineup_summary` and `lineup_leaderboard` use the approved upstream source
  path: `leaguelineupviz` via
  `nba_api.stats.endpoints.LeagueLineupViz`. The raw source dataset path,
  validation, loader, and coverage-gated route execution exist. Missing or
  untrusted coverage keeps the explicit unsupported-data response. Roster
  membership remains rejected as a lineup-unit substitute because it has no
  shared-court, possession, or unit-level sample boundary.
