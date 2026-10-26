# K11 finite population and ownership binding

Owner authorized K11 only, then stop. Base main `d19f1be33bacbb5da7248b50facacf732d473348`. Root `/root` owns the sole maker/integration lane; `/root/k11_checker` independently froze source expectations before application baseline and owns numerical, meaning, unfamiliar-language and validation-gate review. This closes the existing K11 row; PR455 is retained rather than rebuilt.

| ID | Frozen query | Population and scope |
| --- | --- | --- |
| K11-L1 | top 5 scoring games in 2023-24 | 2023-24; league players; pts descending, player-game grain |
| K11-L2 | top 3 assist games vs Celtics in 2023-24 | 2023-24; league players; opponent BOS; ast descending, player-game grain |
| K11-T1 | Lakers players top 5 scoring games in 2023-24 | 2023-24; owner LAL; pts descending, player-game grain |
| K11-T2 | Celtics players top 3 rebounding games vs Knicks in 2023-24 | 2023-24; owner BOS; opponent NYK; reb descending, player-game grain |
| K11-R1 | top 5 scoring games by rookies in 2023-24 | 2023-24; rookies; pts descending, player-game grain |
| K11-R2 | top 5 scoring games by rookies in 1998-99 | 1998-99; rookies; pts descending, player-game grain |
| K11-P1 | top 5 rebounding games by centers in 2023-24 | 2023-24; centers; league players; reb descending, player-game grain |
| K11-P2 | top 3 assist games by guards in 2023-24 | 2023-24; guards; league players; ast descending, player-game grain |
| K11-P3 | top 3 scoring games by forwards in 1998-99 | 1998-99; forwards; league players; pts descending, player-game grain |
| K11-C1 | top 3 scoring games by rookie guards in 2023-24 | 2023-24; rookie guards; league players; pts descending, player-game grain |

Historical classification joins use (`season`, `player_id`) from that season, never current rosters or game-date membership. Named teams in opponent clauses remain opponents. Roster snapshots do not prove participation, injury or medical status. Unknown classifications are omitted with the existing visible incomplete-population caveat and exported row scope; a known-subset ranking cannot claim exhaustive coverage. Missing/empty/wrong-season/schema-less roster files remain unavailable rather than a fabricated zero. Existing controlled safety checks in `tests/test_player_game_roster_coverage.py` remain separate from the ten positives.

Independent frozen oracle [k11-raw-oracle.json](k11-raw-oracle.json), current SHA256 `b2491ba1ba5026bd0c7a853e1b44f7aa8c72adc71fbd8bbb077f26975cd77649`, qualifies eight files against inventory `data-inventory-39158132815`/JSON `d5f72265f5b7baf113ed25d29c65494cb9f3eb40896073b7a657c687ede16f04`. Restored the existing `cloud-backup-39117892814` using its verified archive/manifest and all703file checks. Generation `availability-opening-s4-v1-20261017`, manifest `5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52`; authenticated read-only targeted R2 preflight must reconfirm the active pointer. No data acquisition or publication.

PR455 accepted runtime `86a65f0a` and test successor `7c0693a1`: independent377focused/16raw-controls, broad7725pass, and authenticated19/19zero-skip cases on the earlier immutable generation. Retain that implementation, safeguards and historical review. Its three rookie/center source tests and two team-player list cases cover only part of this binding; their old generation and metric-only comparisons cannot establish current exact rows, full language or deployed acceptance. Its ten ranked-zero tests remain valid historical evidence, not ten K11 population cases. New source assertions cover exact player/game IDs, names, owner/opponent, dates, values/order and scope on the current snapshot.

Freeze before broad validation and final independent review. Reuse unaffected accepted evidence; repeat only missing/invalidated checks and required exact-head CI. Use existing targeted R2/Raw QA and complete-bundle browser workflows, checking actual required execution and zero skips. Existing hosted browser route avoids the known public-site local proxy denial. Preserve PR462/all46absence positives and completed PR533/K09/K10 receipts. K12/full Core-1 and broader capability work remain outside this outcome.


## Baseline and confirmed gaps

All ten population answers selected valid qualified rows on the existing implementation. Independent review corrected oracle assumptions about route/section shape, zero-minute source rows and genuine tied cutoffs; the original prebaseline hash and correction provenance remain in the oracle. Exact identities, values, unique rows and ranked keys remain mandatory, with only qualified equal-key boundary alternatives. Unknown candidate counts are569(2023-24) and1281(1998-99). This is evidence qualification, not a runtime repair.

Six independently frozen unfamiliar wording/entity probes yielded five correct answers and one confirmed leading-season failure: `In 1998-99, rookies top 5 scoring performances` became an unsupported season leaderboard. The control remains a revealed regression, not a fresh held-out success. Existing group-frame parsing now preserves a recognized leading named season when reparsing its population list; controlled during/for forms retain opponent and rookie/position ownership too.

Actual desktop browser baseline also reproduced a population-label defect: the Lakers players top-five list led with “D'Angelo Russell's 5 highest-scoring games” while displaying Davis and James rows. The existing GameLogResult headline must use requested population metadata, even if every returned row belongs to one player; explicit named-player headlines remain separate. Check repaired labels plus exact source-qualified payloads and visible caveats on both viewports. The final browser bundle is ten primary queries plus the one revealed leading-season control.
