# Independent custody executed-revision correction

Reviewer `/root/current123_period_source_review`, separate Codex checker; backend model unavailable. **APPROVED** exact commit9186c8c38b0d4be6f6ef0cb2de65a23fc567579a and a final required integration-plus-custody replay, with no NBA source selector.

The first custody run42369850788 failed its exact summary candidate pin. It was not a passing custody run, and must remain recorded as failed. The root reports all preceding artifact hash/size/inventory/bounds/2-of-2 source-summary checks passed, with failure at the expected6411 versus actual2c82candidate comparison. The numerical integration/new-label selector passed separately; that does not make the two-selector run successful.

The earlier independent custody review repeated the reviewed code revision6411b6b1dbd094bb270c9f7731d3f914f545a045 as the executed receipt revision. That assumption was incorrect and is corrected here with live run metadata and Git ancestry, without weakening any predicate.

Independently verified:

- Source request revision2c82a949825bf64905e1622f7638d6d48dbbc48b is a **direct child** of reviewed code6411b6b1dbd094bb270c9f7731d3f914f545a045.
- The only changed file is newly added `.github/r2-validation-request.json`, containing reviewed_sha6411, unchanged existing production generation and exactly the integration/scorer-book selectors. Every source/app/test/tool/case-data byte remains identical.
- Live GitHub run42369429832 metadata has headSha2c82, eventpush, branchr2-validation/current123-periods-20261107, statussuccess/completed.
- Fix9186c8c3 changes **only** the expected summary candidate literal from6411 to2c82. Artifact13573082492, exact167836byte size/SHA1a788f1f, streaming/expanded/member limits, allowlist,2-of-2 summary assertions, single retained-artifact request and no-NBA protections remain identical. Corrected selector source SHA2560a5bb0d675b63b27c4782ee06bb3824a10cd37df406287a4478d57fa28c833c2.

The final replay validates the new labels and transfers the same retained source artifact. It cannot refetch the game184book, retry NBA transport, declare the earlier failed custody passed, or qualify the PDF's numerical truth merely by transferring it. Original source capture42369429832 remains a distinct successful2-of-2 run on code-identical request revision2c82. No production writes or source values are changed by the correction.
