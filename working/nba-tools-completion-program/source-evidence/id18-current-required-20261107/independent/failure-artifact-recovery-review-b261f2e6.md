# Independent retained failure-artifact recovery review

**Approve** the narrowly bounded recovery helper
`tests/cloud_current123_new16_periods_real_data.py::test_recover_retained_failed_capture_without_source_retry`
at `b261f2e65430d2c6ee7afb2dc0bf5fad86290f30` for the existing read-only
validation runner. Checker `/root/id18_checker`, separate Codex session,
backend model unavailable. This is custody recovery of an existing failed run,
not a repeat NBA request, a period qualification pass or complete snapshot proof.

The helper downloads only fixed artifact13562477912 through the existing
GitHub-authorized route. It enforces the expected16,637-byte package and SHA256
`f56d9c78c3df5c0c81c6d89e06ab99e147dfaa883b7f21a65ce5886bdfaefcfd`, with
100KB streaming cap and thirty-second request timeout. Cross-host redirect
authorization stripping is the standard requests behavior. No token/header,
credential value or signed download URL is printed. Existing permissions and
the dedicated runner are reused; no workflow or credential change is added.

ZIP CRC, safe paths, permitted capture/report member names and the retained
failed summary's exact candidate/count identity are checked before retention.
The original ZIP is retained unchanged in the existing acquisition output.
Logging its exact bounded public-source/request/failure-package bytes provides
a transfer copy within the same existing repository workflow logs, not a
different external recipient. The failure remains one executed/zero passed/
one failed and zero skipped; a successful custody helper must not relabel that
capture as successful or accept unavailable period data.

There is no invocation of the NBA collector, SDK request or source reader in
this separately selected helper. It does not erase earlier attempts, retry the
first failed transport, fabricate unattempted responses, alter source bodies,
write production or relax any validation gate. Actual capture attempt/error/
unattempted ledgers still need inspection once custody recovery succeeds.

Focused descendant delta approval: at
`3bc3dbc806df8a55819ae862191f987a28efac7e`, the helper takes pytest's ordinary
`capfd` fixture and disables capture only around the two already reviewed,
bounded retained-package print calls, with flushing. All fixed artifact, byte,
hash, path, identity and retention checks are unchanged. This makes the intended
same-workflow-log transfer actually visible instead of silently captured by
pytest. **Approve** this exact helper delta; no additional source request,
recipient, credential output or permission is added.
