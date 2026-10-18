# K06 finite comparison binding

This document binds the existing K06 completion-program row. It is not a second queue. The independent checker froze six source-only primary cases in `k06-raw-oracle.json` (SHA256 `bc4738f886e8215597ac6d3f061bb264a7ed65e79952f02d1685189e60554ade`) and six withheld unfamiliar wordings before interpretation. Runtime baseline uses `4b52a7c` (summary/ranking frontend atop `f3a9c6a` backend); no parser or computation edits belong to this lane.

The finite scope is two players' per-game averages over the same named season or date range; a shared named opponent retained on both player samples; two teams' separate season samples versus explicit head-to-head meetings; and a second team pair and player pair. Capture the frames passed to existing `summarize_player`/`summarize_team` to verify complete game/team/player keys even though the comparison API exposes aggregate tables. Compare both summary rows and every requested metric column against independent raw counts, W/L, sums and means. A correct aggregate over the wrong sample is a failure.

Existing controlled anchors: `tests/test_true_head_to_head.py` distinguishes shared matchups from independently scoped samples and keeps primary venue ownership; `tests/test_date_compare_filters.py` fixes opponent/date/window ordering; `tests/test_c1_three_team_compare.py` preserves comparison identity and sample scope. These remain distinct from the actual-source and unfamiliar-language evidence.

Use only the already-qualified 2023-24 regular-season team/player CSVs. The checker oracle's exact source hashes and per-side keys govern the tests. No new acquisition, publication, infrastructure, or runtime authorization is implied. Baseline, independent review, normal CI, actual runner numerical checks and browser/deployment acceptance remain separate gates.

## Original baseline and required checks

The primary baseline at `9db999d` preserves six passing questions before revealing held-out wording. The checker then released `k06-heldout-wording.json` unchanged (SHA256 `973a0ac90f7321f3f7ba55fe5177b20628553bf181cf45bba0b3ab9a9501aa08`); its first results at `d9852b3` preserve two passes and four genuine gaps. A1's “side by side” wording refuses on the wrong player-summary route; B1's “How do Milwaukee and Boston compare” routes to a game finder; B2's “only ... against each other” returns 82-game independent samples instead of four shared meetings; C1's “January 1 through January 31, 2024” loses the lower bound, returning 34 Embiid and 47 Jokic games instead of 9 and 14. Reversed A2/C2 wording passes by entity identity; no positional oracle assumption manufactures failures.

Required selector: `tests/test_k06_comparison_real_data.py` (12 cases, each checks frozen raw truth, complete captured samples, natural/structured results, summary and comparison-table values, and metadata). Original cached execution is eight pass/four fail, zero skips. Existing head-to-head, date-window and comparison fixture controls pass 28/28. Raw QA IDs are `k06_a1`, `k06_a2`, `k06_b1`, `k06_b2`, `k06_c1`, `k06_c2` and each `_heldout` sibling. Twelve desired-positive QA bindings retain requested identity order, including reversed unfamiliar wording; original results are retained under `/workspace/work/k06-qa-baseline/original-twelve`. No failing requirement is marked xfail or weakened. Root owns runtime repairs; independent review, CI, actual runner and deployed evidence remain required.


Runtime repair098f820 reads explicit side-by-side player comparisons, question-form team comparisons and reciprocal games-against-each-other scope. Bare closed calendar ranges retain both endpoints instead of falling through to an open-ended upper date. All12 cached natural/structured selectors and12RawQA pass;23focused checks pass (5unavailable-data skips are not acceptance). Independentchecker verified complete source keys, arithmetic and changed-entity/date probes, approving12numerical+12QA actual validation conditional finalpreflight/CI. Original6primarypass and2of6heldoutpass baselines remain unchanged.

Adjacent limitations retained: malformed name prefixes in comparisons (for example Deven Booker or Mystery Booker with Stephen Curry) can resolve to Booker; this also occurs in the pre-existing Compare path. A medically-cleared clause can be ignored in side-by-side wording. These are not verified identity/status capabilities and remain in the broader qualification work. No broad language-generalization or medical-data support is claimed.

Final cached RawQA:12cases340checks pass. Initial broadpreflight8137passed/1550skipped with one stale-inventory failure after combining K05/K06 corpus; inventory regenerated and docsgovernance passed. Final preflight8,138passed/1,550data-dependent skips; CI39096571461 passed. No runtime edits after independent review.

Actual R2 accepted by independent checker /root/availability_checker: reviewed9252c42f20a06f1b89988976611e64ecc0695ff1, requeste71d1b9ac300f54a75a4ddc418ee807232814842, run39096800744 on queue-d-production-0574735-20260716.12selected/executed/passed, zero skips/errors;12RawQA340checks pass. Numericalartifact12125455448 ZIPd32d7f88fc200aa7d8d9ea96245a05e758265bb9a34c47c724f7feab2113e4c2; QAartifact12123939984 ZIPc77aab88fea000dffd76d6d0749e0ee793bfc36c321dc94d42ca6460cd6edcdb. Reversed order, complete/filtered/H2H/January samples independently accepted. All12manual review fields remain unreviewed; production browser acceptance pending.


October18 normal-development resumption: integrated current main3feb303 into reviewed
`db75d9a880d80511b5384387375bff728aa9f361`; comparison runtime, frozen source oracle
and required cases unchanged from9252c42. Independent checker `/root/comparison_checker`
verified fresh identities/date/opponent/meeting probes, exact raw key sets, W/L and
PTS/REB/AST arithmetic. Current generation `availability-opening-s4-v1-20261017`,
manifest5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52,
has source hashes identical to the frozen oracle. Historical plus/minus quality findings
remain outside this PTS/REB/AST acceptance; full participation completeness is unknown.
Actual run39160471581/requestf373eaf4d21e6f26e0c1905fe814ba527833760e
passed12selected/executed numerical0skips/errors and12RawQA340checks. Numerical
artifact12148476916 ZIP43ed3d48535cf76d7b249e3670d2baeaafbf4b5e03924e15dd494981ca35794f;
QA12148562663 ZIPb8eed298bcfdc1fcd630257b7ea7518e545ed3d2b10c70aaa3df51bdf764b6ff.
Checker physically verified both ZIP hashes and accepted actual results. CI39160306760
and broad localpreflight8228passed1566skipped passed. Skips are not NBA acceptance.
PR492 separately owns40production UI responses; no production data publication.
