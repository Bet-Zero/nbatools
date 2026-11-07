# Independent Mac environment/package review

Reviewer: `/root/mac_environment_checker`, separate Codex checker; backend model identity unavailable. No Claude review is claimed. Verdict: **APPROVED**, subject to ordinary exact-head CI.

Frozen replacement: SHA256 `b6f4d4f156608008bd04b0573f13c1b8223b3bf75ddc2cc5dbad013e9f859e40`.
Embedded environment helper: SHA256 `d7ec68c28d6f0537b3a76c366c037f5596dc1e0cac7e8ef13e6876b20f35a65d`.
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

## Final isolated-cache delta

The final helper differs from reviewed initial commit `0dc0d0bf` by exactly one pip argument: `--no-cache-dir`, which prevents shared user-cache writes during private dependency installation. The generated artifact/binding and two existing exception handoff hashes were rebuilt consistently. Its exact final ZIP/helper hashes appear above.

The frozen artifact checks were rerun against the new ZIP, including actual full196SDK preflight, exact collector/Windows/request preservation, real POSIX shell local-venv bootstrap, actual portable failure receipt and no-rerun custody. Four affected private-setup tests pass (seven unaffected new controls reused); no NBA HTTP was invoked. The unchanged earlier actual isolated dependency-install proof is reused because the added pip cache argument changes cache use, not the pin/index/dependency resolution or source request plan.

The checkpoint body after `Current Core-1 acceptance view` is byte-identical to live main, preserving all46original K08positives and12Core-1bindings. Acceptance baseline SHA256 remains `433f49eb4467401184f15231e0d80520a9d8bef44eb81c5bb4b3988f9f916bfd`. Both existing data-quality records retain every original status, observation, evidence and prepared_handoff field. Their next_evidence points to the repaired Mac package, and a new repair handoff records the frozen hash and zero attempts; neither closes acceptance. No application/data/schema/validator/source transport code changed. Final exact-head CI remains required before merge.

## Final Homebrew locator delta

The bootstrap shell additionally includes the same six finite Homebrew opt paths already known to the helper, for Python3.11–3.13 under `/opt/homebrew/opt/python@3.N/bin/python3.N` and `/usr/local/opt/python@3.N/bin/python3.N`. This covers unlinked/keg-only compatible Python installations under Finder's minimal PATH. No recursive search, provider or installation scope was added. The helper remains exact `d7ec68c2`.

The final ZIP `b6f4d4f1` passed the frozen artifact harness again, including all196 real offline SDK constructions and actual local-venv shell/failure/custody execution. The affected launcher test passed. A separate controlled shell execution mapped only macOS absolute path prefixes into scratch, supplied Python solely at the unlinked Homebrew3.11 opt location with no Python PATH entry, and verified one helper invocation. This is controlled Linux shell evidence, not a native Mac execution claim. All six paths are present, with3.11 preceding3.12. Final README/checkpoint wording accurately separates these checks from NBA acquisition and publication. No further blocking finding remains; final exact-head CI is required.
