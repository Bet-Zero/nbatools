# Official gamebooks: qualified canonical data, remaining credit dependencies

PR582 continues merged PR581/main `cd47ab9d` and the unmerged source-handoff
checkpoint `217c208`. It does not merge that checkpoint branch or fetch the
unchanged archive PBP again. This folder is evidence; the sole active queue
remains the completion-program Resume checkpoint.

## Result and limits

- Game0142 Q3 and H2 are fully qualified for the retained107-game snapshot:
  complete player identities, clocks, counts and all four stored rates.48 player
  rows and4 team rows enter the unchanged pure normalizers and raw validators.
  Coverage is **647/647 windows**.176 source-listed exact rate fractions and16
  additional zero-duration contract cells cover the192 added rate cells.
- Game0138's official Q4 entry at3:04 precedes Tshiebwe's3:03 rebound. A versioned
  event correction, retaining original IDs and an explicit resequencing map,
  restores **104 REB/USG values** across four complete groups.
- Game0009's full Q1 scorer/PBP reconciliation restores **38 AST values** across
  Q1/H1. It corrects Durant's assist, Smith/Adams steal attribution, affected
  whole-game clocks and team assist totals. It also withholds **72 positive-minute
  TOV/USG values** whose complete award credit remains unknown; four zero-duration
  cells retain zero. These72 are outside PR581's original1,365-value population.
- Original population: **953/1,365 qualified;412 unknown**. With the72 newly
  identified unknowns: **484 unknown values in20 groups**. All811 earlier
  independently qualified rates remain exact. Restored original values total142.
- All11 required raw and5 processed structural records pass. All5 standard
  builders execute after affected whole-game inputs change. Full source/numerical,
  R2/current-readiness and production acceptance remain false. The fixed historical
  cutoff is2026-11-05T06:59:31.715470Z with107 exact due IDs and unchanged24-hour lag;
  it is not current freshness acceptance.

## Original custody and exact evidence

[original-capture.zip](original-capture.zip) is the exact808,795-byte Actions
artifact, SHA256 `8ff6e2052f89cf6e0070aee22c5fcee4c83edc7a285a6d7f4c6209135e8b7190`,
Git blob `27969ff1d381ce857b3f39d830685cd990fcf409`. Each exact public URL received
one HTTP200 response, no redirect/retry. The retained receipt gives UTC request
start/end, response URL, Content-Type/Length, Date, ETag, Last-Modified, original
byte count and checksum. Page text is a derivative; PDF bytes remain original.

Capture [42025941403](https://github.com/Bet-Zero/nbatools/actions/runs/42025941403)
binds reviewed candidate `1b86c6f7167d3cfb957450bf28670c578a7ad0ba`, request
`d7445941a3233dfeb9fc257aa12c3e1368f9cbc1`, original artifact13414211446 and the
existing read-only generation. Required selector:1 selected/1 executed/1 passed,
zero skips/failures/errors. This was source transport, not numerical acceptance.
The initial short-body custody review finding was fixed before acquisition;
declared-length mismatches retain `.partial` evidence without an original claim.

| Game | Official PDF original SHA256 | Bytes / pages | Supporting zero-based pages |
| --- | --- | --- | --- |
|0142|`0c56c290a0225b4fefce424932c8960e37db2f5ba5637578f1ec2de00c00b629`|150218 /18|4:Q3 scorer;14:Martin FOR Sasser at2:02;17:delay technical;0/1/2/3/6/7:whole/quarter/half corroboration|
|0009|`7eae719b5ce5dc4d9f1fb2aba7c87b3e1799d7ea672f5e91c74d7c19fd464335`|144675 /20|0/1/2/3:whole/Q1/Q2/H1 scorer;8/9:Q1 PBP, substitutions, unassisted VanVleet6:06 shot and Smith2:23 steal|
|0091|`ec6a686f8746c2ed12da0b2fd88f4f18aa81583fc8fbc0ecc1641029a683ef95`|150020 /20|17:Flagg flagrant1of3/2of3/3of3; types resolved, statistical credit not resolved|
|0118|`771241ca0058d5685474f822809a2176d202f7dce8086e3cf1e8b843c2420f4b`|149871 /20|18:miss1of2 and lane-violation turnover without2of2 or explicit adjudication|
|0138|`1f8ffdff0a2bdeb67ee8acf8cb8b6083ff2ee717982ef7f11fc3e146d54f4389`|148553 /20|18:entry03:04 then rebound03:03;4/6/7:Q3/Q4/H2 clocks|

NBA hosting and visible scorer/PBP authority do **not** prove a different upstream
observer. Production independence remains unestablished. The qualified corrections
rest on specific new literal scorer/event observations, complete source scope,
independent arithmetic and the applicable field-specific authority, not branding
or matching a reported rate/POSS value. Minute tables are internal corroboration.

0142's correction consistently changes the outgoing player's ID, both name fields
and description; it separately types the documented delay technical and technical
attempt. Full-quarter, half and whole-game checks also establish four guarded
whole-game corrections: Sasser plus/minus13→11; Martin6→8; Washington minutes
24:32→exact26:33.6; Sasser23:59→21:57. No validator tolerance changes. The new
cross-grain regression caught those two minute cells before final acceptance.

## Portable preparation and verification

[normalized-snapshot.zip](normalized-snapshot.zip) contains16 ordinary CSVs, a
relative-path SHA256/row inventory, canonical event copies and keyed versioned
correction/unknown/provenance records. A CSV consumer needs no NBA Tools correction
logic. Original HTTP/PDF bytes remain in the separate capture; original event
copies and all proof scripts/receipts are in [verification.zip](verification.zip).
`dataset-manifest.json` distinguishes structural validation, field-scoped numeric
proof, unknown inputs, historical coverage and publication.

The acquisition harness has no application imports. Pure normalization and
validation are reused during a separate offline preparation process. Existing
preparation helpers still import the `nbatools` package, and the old pipeline
module houses acquisition and normalization together: tooling is not independently
packaged yet. The datasets are reusable outside the application. No broad rewrite,
new routine per-game ingester or application runtime exception was added.

The independent Codex `/root/source_checker` verifies source meaning and arithmetic
without the author rate/exposure helpers:1040138+380009+1760142 exact fractions,
PDF starter/substitution lineups, complete count/clock populations, offensive
intervals and literal scorer fields. Separate source-ID maps preserve originals.
The final review records the whole-minute omission and repaired two-cell delta;
earlier approval does not waive that finding. The checker also records its initial
relative-path consumer harness failure and repaired absolute-path execution.

The author runs focused regressions, existing pure normalizers/raw validators,
all5 affected builders, all16 required structural records and actual finder
controls.908,290 original raw CSV tokens are compared against declared changes;
all811 prior exact rates and all other cells survive. Six author finder checks
include Martin Q3/H2 points2/7, Sasser Q3 minutes1.7, Durant Q1/H1 AST2/9 and2/15,
and Tshiebwe Q4 REB1/7/USG1/9. Independent additional Sasser H2 AST2/7/TOV1/6 and
Tshiebwe H2 REB1/7/USG1/9 controls pass.

Ordinary CI exposed an unrelated pre-existing ZIP-fixture timestamp flake on
Python3.12. The test-only fix pins ordinary fixture timestamps and preserves
caller-supplied ZipInfo/security metadata; no runtime assertion or safeguard is
weakened. The first draft broke the symlink fixture and was repaired before
review;35 focused transport/import tests then passed. Exact-head CI and safe
landing receipts belong to PR582; informational development advisories remain
separate from blocking checks.

## Genuine remaining source dependency and next action

[remaining-dependencies.json](remaining-dependencies.json) preserves all484 exact
keys and links the unchanged PR581 dependency ledger. Three logical evidence
packages remain; this is not a minimum file count:

1. Attributable/versioned NBA/scorer/provider methods for take, flagrant,
   retained-ball and canceled awards: TOV trip count, USG numerator and foul-time
   versus attempt-time exposure, and canceled-FT-plus-turnover joint credit.
   These affect the412 original unknowns across0091/0118/0121. The0091 attempt
   ordinals are now documented;0121 awards were already typed.
2. The complete0118 Q4 1:10 award/violation adjudication, including the missing
   second attempt or a documented cancellation and statistical credit.
3. The0009 Q1 award association/credit linking Eason's2:15 made field goal with
   the2:06 one-shot FT. Both clocks appear in the official document. No clock is
   guessed or changed to bypass the unchanged complete-trip gate.

The bounded new public-method search found no qualifying specification. pbpstats
source blob455bfbf0e8a3d21a56bf20e80da1e42dc5d3e214 supplies typed FT bookkeeping
but an assumed missing flagrant trip size; Hoops Junkie's TSA uses a different
metric; NBA-in-R's reported-possession analysis is empirical inference. None
supplies the missing canonical NBA credit contract. Prior glossary/playing-rule
and provider-schema investigations were not repeated.

**Stop on those exact external facts.** Reuse all captured originals and qualified
records; do not restart gamebook/PBP discovery or repeat unchanged bodies. An
existing authoritative method document or source-holder clarification can unblock
preparation without another routine collection approval. No purchase, credential,
permission expansion or outreach occurred. After credit qualification, run the
remaining required numerical/R2/consumer checks and refresh the exact current
24-hour due population before full readiness. Production publication/pointer,
automatic refresh, K08 andK12 remain outside this task.
