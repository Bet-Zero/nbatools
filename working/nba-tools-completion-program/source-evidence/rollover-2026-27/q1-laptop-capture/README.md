# 2026–27 Q1 laptop diagnostic — development staging only

Owner-provided data-only `collection.zip`, captured on the approved backup laptop through the independently reviewed `tools/collect_rollover_q1_laptop.py` helper. This is a **source handoff**, not production data or a published/qualified full-season dataset.

- Exact original archive: [collection.zip](collection.zip)
- Archive size: **7,943 bytes**
- ZIP SHA-256: `ab6618b4b0da9ddd3f262547832718544d74de7cf24d67f4b7901cb9081ef88d`
- Git blob SHA-1: `fc2be95f844e0e9e0c75bf4497d17fa1218495f0`
- Capture: **2026-11-01 18:12:31–18:12:33 UTC**
- NBA Stats endpoint class: `boxscoretraditionalv3` + `boxscoreadvancedv3`, **HTTP 200 / complete** for each, one request per endpoint, `nba_api==1.12.0`.
- Game: **0022600001**, Detroit vs Boston, `StartPeriod=1`, `EndPeriod=1`, `RangeType=1`, `StartRange=0`, `EndRange=28800`.
- Traditional source SHA-256: `613712a1703f8ad393e0c4a48ab782013bb3322a74234a8d514baac35c03c35b`, **13,713 bytes**.
- Advanced source SHA-256: `3f692a446ec0ed1f3cb622353bd1c28c87268f65e73f63dce1c0b879819666ab`, **15,567 bytes**.
- SHA-256 manifest and source file byte counts independently checked before Git staging. The ZIP has five expected entries and is not executable; it contains no request headers or credentials.
- Verified bounded Q1 arithmetic: Detroit **27** points, Boston **28**; player point totals equal team points; both team and played-player minutes total **60:00** each; matched NBA game/player IDs across Traditional and Advanced sources.
- `acquisition.json` reports `source_scope_qualified=true` against its own baked-in oracle, while `canonical_period_accepted=false`. That flag is **not** independent project-wide qualification.
- Retained baseline at capture: `availability-lebron-season-v1-20261031`, manifest SHA-256 `3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3`.

## Codex next action

1. Inspect this exact byte-stable ZIP and verify its hash/manifest before using it. Cross-check original source validity and Q1 semantic/numerical meaning using the repository's existing qualification path and the original summary oracle. Preserve the original `meta.request` strings and metadata; do not substitute the transport URL as the body provenance claim.
2. Treat the Q1 result as **one proof of access**, not proof that historical/current-season period coverage is complete. Independently assess whether this existing laptop route can scale to bounded current-season period source needs, using standing bounded-collection authority and proportional checks; do not ask the owner to run an open-ended manual capture.
3. Continue the **2026–27 readiness** critical path from [PR #571](https://github.com/Bet-Zero/nbatools/pull/571) and the single main Resume checkpoint. Also investigate the 12 same-cutoff player Advanced snapshot/basis conflicts; do not invent TS/USG data.
4. Keep all 11 raw / 5 processed gates, 24-hour exact due-game ID coverage, source authenticity and immutable-generation safeguards. Stage only; any production publication/active-pointer change needs separate owner approval. No paid service, new credentials or permissions, destructive changes, or readiness waiver.

This branch is an external-input handoff only. **Do not merge it into main** or begin deployment solely because the diagnostic arrived. The original LeBron published generation remains unchanged.
