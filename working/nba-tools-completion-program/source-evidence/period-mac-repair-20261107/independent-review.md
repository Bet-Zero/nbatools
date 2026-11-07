# Independent Mac environment/package review

Reviewer: `/root/mac_environment_checker`, separate Codex checker; backend model identity unavailable. No Claude review is claimed. Verdict: **APPROVED**, subject to ordinary exact-head CI.

Frozen replacement: SHA256 `b197537a510deea6731a8b89ed516bfce423e55761ae682b22015ec713bcf5f4`.
Embedded environment helper: SHA256 `cf17dd49004c0bb69cb03fe78edd1cd12c0a41ad6b06f19a0d586b9a1b246ab8`.
Collector remains byte-identical to PR600, SHA256 `97bb73b6473fb532b249fa1daaa7f9089541d5b39b5d555bfac4248f9dce83e9`.
The exact canonical request remains SHA256 `19cc7759dd2dec7676888538b574e3dd316d6b58712b2b30d42c9b92911a9a52`, 196 jobs. Original PR600 ZIP and Windows launcher are preserved.

The original weak probe was independently reproduced: an importable namespace `nba_api` passes `import nba_api` while `importlib.metadata.version('nba_api')` raises `PackageNotFoundError`. This proves the detection defect without assuming the owner's private filesystem. Retained PR572/573 comments establish earlier installed isolated-environment use, and `tools/build_readiness_recovery.py` establishes finite local/parent venv discovery. An exact historical Python3.11 installer command was not found or invented; the user supplied the prior Python3.11 context.

Initial review found two environment-discovery gaps: the Mac bootstrap itself omitted existing virtual environments, and the helper could invoke the Apple developer-tools stub despite the shell guard. Both were corrected before this frozen review. Setup failures retain bounded stage/reason/exit-status evidence; raw installer output is omitted to avoid possible proxy-secret disclosure.

Executed independently on the extracted frozen artifact:

- ZIP integrity, executable Mac member mode, unchanged original collector/Windows bytes, exact embedded request and hashes.
- Full real offline SDK preflight of every 196 request via the extracted helper, Python3.12.14/nba_api1.11.4. Endpoint construction uses `get_request=False`; no NBA transport.
- Actual shell execution with a spaced extraction path and retained local `.venv`, without a Python PATH dependency. Exactly one helper invocation follows bootstrap admission.
- Actual extracted-helper setup-failure path: portable existing-protocol ZIP, all member lengths/hashes valid, zero attempts, 196 unattempted, no accepted data or production write.
- Rerunning the helper with that existing output preserves exact bytes and does not prepare or invoke collection.
- No-bootstrap embedded fallback explicitly labels its timestamp as package preparation, not an actual laptop capture.
- All 11 focused new tests passed independently, including isolated setup failure/success control flow, `-I` environment contamination protection, private pinned binary-only PyPI install arguments, source-job no-retry/custody and single collector invocation.

Parent-reported real clean private-environment installation and full SDK preflight are separate evidence, not relabeled independent executions. Unchanged prior collector transport/partial-byte/timeout/custody checks and NBA application/numerical evidence remain applicable without rerunning broad suites.

No physical macOS/Finder execution environment was available. The executed evidence is Linux shell/runtime and controlled environment testing; it is not a claim of native Mac validation or newly collected NBA data. This change is acquisition setup only. No NBA requests executed, no new period windows acquired, no source values changed, and no production publication or pointer/protection/credential/permission/cost/refresh action occurred. Period completeness remains false; all 98 new windows remain missing until qualified original responses return.
