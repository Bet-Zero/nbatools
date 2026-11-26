NBA TOOLS

# Final execution plan

Deliver Cleveland. Stabilize the accepted product. Qualify growth.

25 November 2026 | Final reviewed version 2 | America/Detroit

The [Resume checkpoint](README.md) owns live status, receipt applicability and
the next action. The reviewed baseline and sequence below preserve the November
25 contract. Reconcile them with current evidence before acting.

The execution direction is settled. Restore useful snapshot monitoring, finish the qualified Cleveland release through the protected route, then close the shared correctness, resource, repeatability and maintenance defects. Expand through a measured, reusable pipeline.

This is the complete execution document. It incorporates the original architecture findings, the additional review supplied by the owner and a final independent check of the recommendations. The finding definitions, implementation entry points, tests, release protocol and completion criteria are included here; an agent does not need the earlier PDFs or chat to understand the assignment.

Version 2 supersedes execution plan version 1 and the execution sequencing in the architecture review. Original evidence remains historical. The plan has been finalized; its repository adoption, code changes and protected operations are assigned work, not claimed as performed by this review. [R51] [R52]

| Execution priority | Required result |
| --- | --- |
| 1. Restore visibility | All monitor checks run; snapshot health and the unresolved Live requirement are reported separately. |
| 2. Finish Cleveland | One exact candidate, applicable cold proof, guarded activation, all registered deployed controls and candidate backup/restore. |
| 3. Stabilize once | Shared identity/integrity fixes, bounded requests/resources, reproducible builds, accurate UX and a replacement for repeated historical evidence resealing. |
| 4. Grow deliberately | A representative next slice demonstrates useful coverage, recurring effort, storage demand and recovery before bulk or recurring publication. |

Checked baseline: main 718d4ac5; production deployment READY; Cleveland preview qualified; production data activation pending. Changes during later execution are reconciled against this baseline before acting. [R03] [R05] [R07]

## Contents

- [1. Decision and starting point](#1-decision-and-starting-point)
- [2. Execution order and operating contract](#2-execution-order-and-operating-contract)
- [3. Work packages](#3-work-packages)
- [4. Exact Cleveland release and recovery protocol](#4-exact-cleveland-release-and-recovery-protocol)
- [5. Verification, measurement and growth decisions](#5-verification-measurement-and-growth-decisions)
- [6. Completion and first execution assignment](#6-completion-and-first-execution-assignment)
- [Appendix A. Findings and closure map](#appendix-a-findings-and-closure-map)
- [Appendix B. Disposition of the additional review](#appendix-b-disposition-of-the-additional-review)
- [Sources and evidence](#sources-and-evidence)

Owner reading path: sections 1, 2 and 6. Implementation lead: read the full plan, then use the work packages and release protocol. Appendix A defines F1-F15; Appendix B resolves every substantive recommendation from the additional review. The existing Resume checkpoint remains the only active task queue.

## 1. Decision and starting point

### The product and the completion claims

NBA Tools is a natural-language NBA statistics website backed by one deterministic Python engine shared by the web app, API and CLI. Questions must retain their intended subject, conditions, sample and metric. The documented historical destination begins in 1996-97; wider combinations, participation and Live capability retain their original requirements. Keep the engine, result contracts, React app, qualified sources, immutable data versions and independent numerical expectations. Keep CSV/Pandas initially; a measured constraint determines any later format or host change. [R01] [R02]

Use four separate claims: Cleveland delivered; accepted snapshot stabilized; next expansion qualified; full original/Live product complete. The historical K08 ledger remains 16 PASS / 26 MISSING DATA / 4 LIVE. Missing data does not become a passing answer, an accepted refusal or a deleted requirement. Cleveland's selected-team appearances and rostered missed games remain distinct. [R03]

### Facts rechecked for this final pass

| Area | Verified starting point / practical consequence |
| --- | --- |
| Serving release | Main is 718d4ac5877df2051e29fbdd2b610f8724dafb35; production deployment VGmn1JWbDGRWYMj9PMEMpxaaya7f is READY. PR 643 removed original-source replay from qualified serving. Preserve that correction. [R05] [R07] |
| Cleveland | Preview 5986dde5 returned 31-13 in 44 games without LeVert in 5.8248 s, with the accepted cold indicators and six follow-ups. The candidate is uploaded but its production activation remains pending in the current receipt. [R03] [R05] |
| Monitoring | The 15 latest reviewed scheduled monitor runs failed. In run 45594140692, health passed, readiness failed on new_season_not_loaded and the representative query did not run. This establishes lost query-monitor coverage, not weeks of proven website downtime. [R10] [R53] |
| Build inputs | Both reviewed preview and production build logs identify Python 3.12 and uv 0.13.5, but provide no complete resolved-package inventory. Both say the vercel.json memory setting is ignored on Active CPU billing. Do not infer actual package equality or a 1024 MB worker limit. [R07] [R08] |
| Existing recovery | The November 17 cloud-backup-44062070685 release and successful workflow cover the current active generation, including a separate credential-free restore. Reconcile and reuse this evidence; the October receipt is not the newest backup. No new restore was run for this plan. [R54] [R55] [R56] |
| Continuity | The checkpoint top labels are stale even though its later cold receipt is current. W0 reconciles them. The active working folder has operational consumers and must remain tracked until migrated. [R03] [R36] |

### Decisions that may actually reach the owner

These are preparation requirements for the lead, not requests for approval now. Reuse any authority already granted for the same action and scope. Routine engineering, review and permitted integration continue under the project instructions. [R01]

| When | Concrete decision packet |
| --- | --- |
| Cleveland ready | Exact activation, scoped historical-snapshot verifier/monitor/recovery semantics, and explicitly scoped recovery contingency. Include any genuinely required additional protected cold qualification and its bounded budget. |
| Measurement exposes a limit | One recommended resource, duration, hosting, cost or material service-contract change, with measured consequences. Reserved Vercel settings remain reserved even when represented in a repository file. |
| Growth requires retention changes | An explicit retention/reachability/deletion policy, affected objects and verified recovery. No deletion by inference from storage pressure. |
| Live milestone | Exact data scope, refresh schedule, freshness and recovery design, and authority for any unattended publication. League-wide participation is an existing goal; ask about a real tradeoff only. |
| Governance change selected | A concrete required-check/settings configuration that works for a solo owner. Pending access is recorded; it does not become an unrelated Cleveland prerequisite. |

## 2. Execution order and operating contract

### The critical path

| Stage | Work and order | Exit |
| --- | --- | --- |
| 0. Adopt and reconcile | W0: current main/open work/checkpoint, exact data/release receipts, protected authority, deployment route. W5A: collect actual build inputs read-only. | A fresh agent has one self-contained plan, one queue, actual gates and the next task. |
| 1. Deliver Cleveland | W4A restores run-all monitoring. W2 leads protected activation preparation. Allow only the necessary operational/build changes before the final freeze. W1 can be authored/reviewed independently and normally merges afterward. | Applicable cold qualification; all 87 registered deployed checks at this baseline; exact data verification; new-candidate backup and independent restore; website capability usable. |
| 2. Stabilize the snapshot | Merge W1. Complete W3A request/clock corrections, W5 build binding and W4B UX. Prepare W6A evidence replacement. Freeze the coherent artifact; run final W3 qualification and required broad release checks once. | Section 6 stabilization criteria all hold. Later work has an owner and trigger; no arbitrary seven-day hold. |
| 3. Expand and deliver Live | W7 starts with the next participation scope change/shared-cause defect. W8 qualifies the next useful slice and recurring economics. W9 completes Live delivery after the applicable storage/operations gates. | Qualified scope and sustainable cadence demonstrated. Full original acceptance still uses its unchanged requirement ledger. |

The Cleveland generation preserves the relevant player/name inputs. The shared version race alone is therefore not a demonstrated reason to delay this exact candidate. A concrete candidate-relevant integrity or correctness failure does take priority. The incomplete required-object fallback remains assigned repair work with consumer-level acceptance; ordinary successful queries do not prove that failure behavior is safe. [R09] [R49]

If a protected action is waiting, continue independent authorized implementation and review. Keep unrelated deployment-affecting changes on their branches while the Cleveland artifact is frozen. A necessary repair that changes the artifact triggers the relevant evidence decision below, not a silent reset of the preview budget.

### Freeze all inputs that can change the served result

The lead records one release identity: serving code and built deployment, interpreter and available resolved dependencies/lock, relevant nonsecret configuration, data generation/manifest, qualification conditions and actual operation budget. A code revision alone does not identify the complete runtime.

The freeze covers frontend, monitoring, tooling, documentation and build changes whenever the actual delivery rules would rebuild production. Calling a change frontend-only or monitor-only does not establish that the Python artifact is unchanged. W4A and W2 may form the minimum pre-activation operational release; reconcile its deployment effects once and preserve all unaffected source/numerical proof.

Matching package lists is one input to an applicability decision, not sufficient proof. The reviewed build logs do not contain those lists. Missing older inventory is recorded as unknown; it does not by itself revoke an explicitly accepted prior receipt or establish reproducibility. If a necessary new build cannot inherit the relevant proof, bind the new inputs and qualify that artifact within actual authority. Prepare one consolidated, conditional qualification/activation packet if additional authority is needed. Activate only after its qualification conditions pass. [R01] [R05] [R20] [R25]

### One canonical home for each kind of information

| Repository destination | Authoritative content / landing rule |
| --- | --- |
| working/nba-tools-completion-program/execution-plan.md | The active sequence, work packages, completion criteria and self-contained findings appendix. This is the W0 destination. |
| working/nba-tools-completion-program/README.md | The current lead, active task, status and one next action. Keep this as the only queue. |
| AGENTS.md | Standing authority, proportional checks, evidence reuse and archive protection. Reconcile still-applicable inherited safeguards once; retain genuine restrictions. |
| docs/operations/deployment.md and recovery.md | Executable activation, verification, backup and recovery procedure. Land with the justified operational/code change and account for deployment effects. |
| docs/audits/ | Historical findings and review decisions, promoted from the self-contained task appendix in an already-justified change. No private PDF access is required to interpret F1-F15. |

The working/ location supports light classification, but a first-branch push with no trusted prior build can still build. W0 checks the actual route. Do not disguise work as a validation branch or weaken delivery selection. The entire completion-program folder remains tracked until W6B migrates every affected operational/evidence consumer and proves clean checkout/restore. [R24] [R36] [R69]

### Ownership, verification and paperwork

The integration lead named in the checkpoint owns delivery. One writer owns shared parser/request/service code at a time; at most one genuinely independent implementation lane runs alongside, plus a separate checker. Set file and contract ownership before editing. A checker reviews a frozen revision and chooses independent meaning, failure and numerical probes.

Use focused tests while editing, actual required CI and affected read-only R2 checks before merge, then the existing once-per-frozen-release broad gates. Retain exact-head requirements and all required assertions. A skipped or empty required selection does not pass. Reuse unchanged source evidence and independently accepted results within their actual scope; changes to runtime/build/data require the affected checks. This rule belongs in AGENTS, not a second permanent rulebook. [R01] [R37]

Keep evidence and checkpoint changes in the logical work PR. A separate record-only PR needs a real stop/new state with no work PR to carry it, or a need to preserve a frozen candidate. PR count is not a completion target. No unsupported calendar estimate or 12-18-PR commitment is imposed.

Resource/duration settings, access, protection, publication gates, new costs and destructive changes remain governed by their effect and existing authority, regardless of file location. Application deadline logic and reviewed build-selection code can be repaired within that authority; a repository edit is not a permission bypass. No monitoring agent is implied when no session or real automation is active.

## 3. Work packages

Paths and symbols below are verified entry points at main 718d4ac5. Existing test names guide focused selection; new scenarios are identified explicitly. They do not require every listed suite on every PR. Implementation must trace the current consumers before editing, retain unchanged numerical truth and use the smallest coherent change.

### W0 - Adopt a self-contained plan and accurate checkpoint

Responsible: Integration lead. Sequence: First, with a short live-state reconciliation.

**Problem and entry points.** The checkpoint has old top-level runtime labels, the v1 plan points to a deployment-triggering docs/ location, and F1-F15 depend on an external PDF. AGENTS also inherits unspecified older safeguards. Entry points: AGENTS.md; ROADMAP.md; working/nba-tools-completion-program/README.md; tools/delivery_scope.mjs::{classify,select}; docs/operations/working_and_archive_policy.md. [R01] [R03] [R24] [R36] [R81]

**Change.** Place this plan's active sequence, work packages and Appendix A in working/nba-tools-completion-program/execution-plan.md, with one checkpoint link. Correct the current source/runtime/data/receipt labels. Preserve the original acceptance ledger, parked work and saved branches. Reconcile inherited rules once into the current contract; make practical delivery part of completion for affected paths. Add immediate protection against archiving the load-bearing task folder. Distribute standing rules and runbooks as section 2 specifies rather than duplicating them. Check the actual branch/build route before landing; defer historical docs promotion to a justified operational/code change if it would disturb the frozen release.

**Verification.** Run make docs-governance and git diff --check, accurate self-review and the actual applicable CI path. Use tests/test_docs_governance.py and tests/test_delivery_scope.py only when their behavior changes. A fresh independent agent must locate the current task, authority, candidate, requirements, F1-F15 and exact next step using tracked files.

**Done when.** The checkpoint is accurate, the plan is executable without private chat/PDF access, genuine safeguards remain, archive protection is explicit and the next action leads to W4A/W2. Record any actual build rather than asserting that Markdown cannot deploy.

**Boundaries.** No application suite solely for prose; no new queue or status system; no application/data/settings mutation implied by adopting the plan. The original audit is retained as evidence, not rerun.

### W4A - Restore snapshot monitoring before activation

Responsible: Operations writer with lead integration and independent checker. Sequence: Prepare and prove run-all behavior before Cleveland activation; policy changes follow the exact authority described below.

**Problem and entry points.** src/nbatools/production_monitoring.py::run_production_monitor stops at the first failed case; strict readiness precedes the query. Its default cases, _run_monitor_attempt and _safe_response_summary define the actual contract. tools/production_monitor.py and .github/workflows/production-monitor.yml run it every two hours. docs/operations/observability.md and recovery.md define approved alert and recovery policy. [R10] [R53] [R57] [R58] [R83]

**Change.** Run all configured health/readiness/query checks and aggregate outcomes. Report strict Live readiness separately from snapshot-service status. Parse blockers as the actual typed objects with code fields. A snapshot exception requires exactly one well-formed new_season_not_loaded blocker, the expected immutable active generation, expected response schema/status, and passing health/query checks. Any extra, duplicate or malformed blocker, wrong generation, transport failure or failed query is actionable. Preserve strict ready=false and its 503. Before any policy approval, run-all reporting can operate while retaining the existing strict overall verdict. Include the proposed alert/publication/recovery classification in the one concrete Cleveland packet. Distinguish snapshot incident recovery from unmet Live scope without rewriting historical availability or owner-approved full/Live objectives.

**Verification.** Extend tests/test_production_monitoring.py and tests/test_production_monitor_workflow.py. Replace test_readiness_http_error_is_semantic_and_skips_query with run-all cases; cover simultaneous known Live gap plus a real query failure, wrong generation, malformed/duplicate blockers, bounded retry, latency and privacy. Run the existing workflow against the actual deployment after merge and confirm subsequent scheduled execution includes the query. [R60] [R61]

**Done when.** The representative query executes despite earlier failures; snapshot regressions remain visible; any changed pass/alert semantics are explicitly authorized; receipts identify both snapshot and Live status. The lead records actual scheduled coverage and continues normal observation.

**Boundaries.** Do not change the readiness endpoint to claim Live readiness, add broad 503 tolerance, create a second monitor or invent recipients. No seven-consecutive-day waiting gate. Monitor source/runbook changes can rebuild production and must follow the release freeze/applicability rules.

### W2 - Complete protected Cleveland activation and recovery

Responsible: Publication writer; integration lead owns the complete release; separate checker. Sequence: Lead delivery task after W0; W4A monitoring and W5A input inspection precede the final activation decision.

**Problem and entry points.** The workflow/CLI/registry expose validate, publish and upload_candidate, but not the existing activate_r2_candidate operation. tools/r2_publication.py::verify_published_snapshot waits for strict ready=true before running answers. Entry points: that module's main, check_main_revision, check_environment, check_live_answers; generation_publication.py::{activate_r2_candidate,verify_r2_candidate,_candidate_base}; .github/workflows/r2-data-publication.yml and r2-publication-readonly.yml; .github/data-publication-packages.json; existing validation/backup caller and resolver. [R16] [R17] [R18] [R50] [R80] [R82]

**Change.** Expose a reusable protected pointer-only activation mode consistently through workflow, registry, resolver, CLI and receipts. Preserve merged-main/post-CI validation, same-base protection, independent read/write credentials and owner environment gate. Implement the narrowly scoped snapshot verifier alongside strict Live readiness. Extend the existing post-publication backup/restore path to activation. Bind the exact objects, build evidence, budget and recovery described in section 4. The activation itself writes zero snapshot objects and one conditional pointer; it never repeats the candidate upload.

**Verification.** Use tests/test_candidate_generation.py, test_r2_publication_gates.py, test_generation_publication.py and the affected test_r2_publication_real_data.py cases. Preserve test_activation_compare_and_swap_rejects_race_without_reupload and test_backup_only_follows_approved_published_and_verified_generation, extending the latter to approved activation. Add wrong/stale base, changed receipt, missing authority, malformed readiness, repeated dispatch, uncertain outcome, later-publication rollback guard and failed backup/restore cases. Run every registered deployed check: 87 in the current Cleveland registry, with existing pacing and bounded retry. [R62] [R63] [R64] [R65]

**Done when.** The exact candidate is activated under applicable authority, pointer and every required object/control are independently verified, the candidate has a durable byte-exact backup and separate credential-free full restore, and the intended public website answer works. Record delivered only then. If only an owner gate remains, report the exact ready action and continue independent authorized work.

**Boundaries.** No ad hoc low-level write, legacy combined upload/publish, unrelated source collection, broad exception to readiness, or undocumented operation-budget reset. Previous-generation recovery evidence does not replace candidate backup/restore. The detailed phase-specific contract in section 4 is mandatory.

### W1 - Make player identity immutable per data version

Responsible: Shared-runtime writer and independent checker; lead integrates. Sequence: Author/review beside W2 only with independent files. Normally merge after Cleveland delivery; move earlier only for a demonstrated candidate-relevant failure.

**Problem and entry points.** src/nbatools/commands/entity_resolution.py::_ensure_player_index_generation and reset_player_index share/reset eight module-level fields. _read_player_names skips failed season reads; _read_published_player_names catches required-ledger read failures. Consumers include player_ids_for_name, canonical_player_names_by_id and name matching. The request's data context is in data_source.py. [R09] [R14]

**Change.** Build one immutable identity bundle per source, generation and trusted manifest identity. The request retains its bundle; names, IDs, canonical spellings and indexes travel together. Coalesce/atomically publish construction, permit old/new in-flight bundles to coexist and bound retired entries. A failed construction publishes nothing partial and cannot poison a later valid build. Propagate

missing/hash/size failures for required published objects through real consumers. An explicitly optional unlisted legacy ledger may use a deliberate complete fallback, but every declared required fallback input must validate. Avoid a global lock over complete queries.

**Verification.** Extend tests/test_entity_resolution.py, test_player_identity_collisions.py, test_player_identity_prefetch.py, test_data_source.py and affected real-data identity tests. Add an additive same-name collision interleaving through the actual admitted executor; each old/new request must keep its own IDs and spelling. Add failed concurrent initialization/retry, required-ledger corruption, and the compound ledger-plus-season failure that could otherwise erase ambiguity. Verify natural and structured consumers, not just dictionary access. Independently check expected samples and unknown/empty behavior.

**Done when.** Focused regression, applicable blocking CI, affected real-data run and independent review pass; no mixed-generation identity or confident partial identity is possible in the tested failure cases. Evidence is reconciled for any changed hosted artifact.

**Boundaries.** No parser rewrite, new manifest framework, source requalification, changed participation meaning or coarse query-wide lock. The general race is not represented as a proven failure of the identity-preserving Cleveland package. [R49]

### W5 - Bind production inputs and make deployment selection reliable

Responsible: Build/CI writer under the lead; independent checker for selection and integration. Sequence: W5A reads actual deployed inputs at entry. W5B binds the chosen build before final W3 qualification; before activation only if a necessary new artifact requires it.

**Problem and entry points.** pyproject.toml has broad dependency ranges and no tracked Python lock; production, CI and R2 jobs can resolve different inputs. Entry points: pyproject.toml, the actual Vercel Python build input, .github/workflows/ci.yml, r2-real-data-validation.yml, tools/delivery_scope.mjs and tests/test_delivery_scope.py. The observed deployment uses Python 3.12; the matrix and monitor have other legitimate contexts. [R20] [R21] [R24] [R40] [R80]

**Change.** Capture interpreter, complete resolved runtime dependencies when obtainable, relevant build/configuration and artifact identity without secrets. Do not infer installed packages from allowed version ranges. Adopt a production-consumed lock/bound dependency graph and align the production-equivalent CI and R2 path. Keep wider Python compatibility testing deliberate. A new lock is a new build input and receives affected checks. Add bounded dependency-advisory triage and required action pinning without hiding advisory failures. For first-branch preview selection, use an actually built equivalent baseline or a reviewed trigger that cannot hide unbuilt application changes. An arbitrary merge-base is insufficient. Preserve conservative mixed/unknown/deleted inputs and authorized environment redeploys.

**Verification.** Use test_vercel_runtime_imports_are_direct_project_dependencies, test_vercel_package_stays_within_hobby_function_budget and test_vercel_source_upload_excludes_local_data_and_evidence in tests/test_vercel_functions.py. Preserve test_runtime_then_receipt_cannot_hide_unbuilt_or_unchecked_runtime, test_unknown_baseline_is_conservative, test_missing_shallow_history_is_conservative, test_no_change_same_revision_redeploy_is_not_suppressed and test_explicit_environment_redeploy_can_force_a_newer_docs_revision. Add first-push trusted-built-base and unbuilt-main cases. Confirm actual deployed lock consumption and inspect real bundles. [R68] [R69]

**Done when.** The chosen production-equivalent build has repeatable inputs; final resource evidence identifies it; legitimate pure checkpoints avoid builds when a safe basis exists; real/uncertain application changes build. The minimum required-check proposal is concrete and any reserved setting still pending is accurately recorded.

**Boundaries.** No claim that a new lock reconstructs unknown older packages, no arbitrary pandas major upgrade or broad toolchain migration, no suffix-only CI bypass, no optional branch-setting access as a Cleveland/stabilization blocker, and no owner role as routine merger.

### W3A - Bound request input, limiter state and response deadlines

Responsible: Shared-runtime writer with independent failure review. Sequence: Early stabilization after the frozen Cleveland delivery; can be prepared while a protected operation waits.

**Problem and entry points.** JsonHandler.read_json_body in src/nbatools/vercel_http.py reads the declared length before applying limits. admission_control.py holds per-client timestamp dictionaries indefinitely and starts a 20-second execution timer inside an entry configured for 20 seconds. That leaves no proven startup/response margin. Entry points: JsonHandler.read_json_body, BODY_LIMITS, AdmissionController.run_query/reserve_feedback and timeout completion handling. [R12] [R13]

**Change.** Reject excessive declared length before reading and bound actual reads for the deployed adapter. Keep the existing endpoint limits: 4 KiB query; 8 KiB structured query/feedback. Handle malformed, missing, negative and truncated lengths deliberately. Expire inactive limiter keys using bounded cleanup while preserving active windows and reservation rollback. Set the internal deadline from the actual effective host/request budget with measured allowance for initialization, parsing, serialization and response completion. Use remaining time in downloads/long work where applicable; keep a slot occupied until the underlying work ends. Align the public error and frontend deadline with the total response budget.

**Verification.** Extend tests/test_vercel_functions.py around the real JsonHandler; prove an excessive length causes no body read and actual reading cannot grow without bound. Preserve test_body_byte_limit_is_inclusive_and_uses_encoded_bytes, test_fastapi_rejects_body_before_json_parsing, test_shared_query_rate_limit_returns_retry_after, test_feedback_quota_counts_only_committed_acceptances and test_timeout_keeps_slot_reserved_until_worker_finishes in tests/test_admission_control.py. Add many expired clients with active-window preservation and real response completion near the chosen deadline. [R67] [R68]

**Done when.** Input and stale-key growth are bounded, valid requests still work, rate-limit/timeout responses retain status and retry information, and measured margin exists for a useful response. Capacity claims wait for W3C after build freeze.

**Boundaries.** A guessed 16-17-second constant is not acceptance. Do not silently cut supported queries, accept timeouts as positive answers or change reserved host settings to hide the defect. No broad full-suite run for each small repair.

### W3B - Correct request clocks and literal calendar dates

Responsible: Shared-runtime writer and checker familiar with the retained date contract. Sequence: During stabilization, as a deliberate date-boundary change; positive Live delivery remains W9.

**Problem and entry points.** _seasons.today() uses the host-local date; _date_utils.CURRENT_QUERY_DATE is captured at import; natural_query.py also reanchors relative windows to a stale data cutoff. One clock alone would leave the anchoring defect. Entry points: _seasons.py, _date_utils.py::extract_date_range, natural_query.py date/season consumers and propagation into the admitted worker. [R28] [R30] [R71]

**Change.** Capture one immutable America/Detroit clock for each request and carry it through its admitted worker. Explicit today, yesterday, tonight and current-season requests use that clock and the existing season-calendar rule, never the data cutoff. Preserve explicit season labels, absolute dates, omitted-season defaults to the served snapshot and last-N-game meanings. Uncovered literal dates/seasons return precise unavailable coverage, not an older interval presented as the requested

answer. Label existing latest-available snapshot behavior separately with its cutoff; do not add a broad new query language just for this repair.

**Verification.** Extend tests/test_season_rollover.py, test_natural_date_queries.py, test_explicit_date_ranges.py and affected test_fuzzy_weeks_date_range.py cases. Cover two requests across midnight/season rollover in one long-lived worker, concurrent independent clocks, stale-snapshot literal requests, timezone boundaries and unchanged absolute/default/last-game controls. Preserve historical captures; change only affected current expectations with explicit meaning and independent review. [R72] [R85] [R86]

**Done when.** The clock is request-scoped; literal calendar scope cannot be silently replaced by old data scope; retained snapshot/default behaviors remain correct. W4B examples and labels agree with this behavior.

**Boundaries.** No new NBA collection, current-season publication or unattended refresh. An unavailable literal-current answer does not pass an original Live positive or finish the Live milestone. Preserve every unmet Live requirement for W9. [R01] [R02]

### W3C - Qualify the complete supported workload and K12 scope

Responsible: Runtime writer measures; lead fixes the workload once; checker validates meaning, resource claims and independence. Sequence: Diagnose early if useful. Final acceptance follows relevant W1/W3A/W3B/W5 changes and the coherent code/build/config/data freeze.

**Problem and entry points.** The current service lacks complete demonstrated resource limits across meaningful paths. Existing K12 distinguishes controlled process-cold evidence from actual deployed cold. Entry points: admission_control.py, data_source.py, commands/data_utils.py, dataframe_cache.py, query_service.py, candidate_preview.py and working/.../k12-binding.md. [R04] [R11] [R12] [R14] [R29] [R47] [R73]

**Change.** Measure common summary/ranking, team record, appearance WITH/WITHOUT, rostered absence and unknown coverage, costly actually supported history, materially different broad aggregation, cache eviction/redownload and version rollover. Admit three representative requests together in one otherwise idle worker. Record external full-request time, objects/bytes, rows, process peak and incremental memory, live/cache/disk state, active work and completion. Distinguish configured limits from effective deployment resources. Repair measured amplification with prepared facts, early filtering, bounded cache/index lifecycle, safe streaming or incremental aggregation. Preserve every requested filter, sample and unknown.

**Verification.** Use tests/test_k12_delivery_real_data.py::test_k12_answer_delivery, tests/test_deployed_k12_delivery_browser.py and affected data-source/cache/admission tests, with retained independent oracles. For K12, reuse the cold instrumentation mechanism but adapt its appearance-specific validator to the actual S1/R1/B1/M1 and H1 paths. Keep common cold <=10 s, warm p95 <=3 s and admitted historical <=20 s under their existing sampling contract. Prove unprimed first-query context, cache state, exact artifact/data and external elapsed time; the header begins after imports/body reading. Preserve test_cold_evidence_survives_real_admitted_executor and test_cold_verifier_requires_actual_cold_positive_answer. [R04] [R62] [R74] [R75]

**Done when.** All admitted requests return independently correct answers within the declared measured limits; excess rejection is tested separately; memory/disk/eviction and useful failure behavior are bounded. Close the exact K12 deployed-cold requirement only if its full scope, environment equivalence and authority are satisfied. Otherwise state the precise open part and the prepared bounded next action.

**Boundaries.** Cleveland's one <=20 s result does not close K12's common <=10 s cases. K12 chasing is currently parked: use the credible new method in a bounded authorized task, never reset Cleveland's budget or resume open-ended log chasing. If three requests cannot fit, compare lower per-worker concurrency as a measured alternative with actual end-to-end success/latency/429 behavior; do not call it equivalent because the host autoscales. Any material
service/safeguard change receives its actual decision. Stop optional measurement once named risks and required gates are covered.

### W4B - Make discovery, coverage and errors match the product

Responsible: Frontend writer where independent; runtime writer owns the API contract; lead integrates. Sequence: Prepare against a stable contract; merge after the Cleveland freeze and qualify on the actual stabilized release.

**Problem and entry points.** SampleQueries.tsx advertises literal-current questions and some unverified examples; api/client.ts loses useful structured failure information. App.tsx already owns request cancellation and stale-response suppression. Entry points: frontend/src/components/SampleQueries.tsx, frontend/src/api/client.ts, frontend/src/App.tsx and operational_observability.py. [R31] [R32] [R33] [R34]

**Change.** Feature independently verified questions against the active snapshot, with explicit covered seasons/windows and clear cutoff/partial/unknown scope. Do not blanket-substitute 2025-26 without verifying each example. Preserve appearance-for-selected-team, rostered absence, opponent and injury/on-court distinctions. Carry status, retry timing and request ID in a small structured client error; handle non-JSON host timeout, network failure, rate limits and unavailable coverage. Keep AbortController/latest-request ownership and avoid automatic retry loops or technical clutter in normal results.

**Verification.** Use existing frontend unit tests/build/lint with locked installation; add focused error-contract and sample-question checks around the changed components. An independent agent exercises fresh desktop/mobile discovery, a correct scoped answer and recovery from a useful error. Check changed keyboard/focus behavior. Use retained source expectations and verify the exact sample season/window, not merely successful rendering.

**Done when.** Featured questions work; the user can understand sample and coverage; failures retain useful status/retry/request identity; stale responses remain suppressed; changed surfaces are usable on desktop and mobile.

**Boundaries.** No owner's manual QA assignment, no premature Live or league-wide claim, no public query-feedback persistence, and no frontend-only exemption from deployment freeze. Default snapshot behavior remains available and accurately labeled.

### W6A - Replace repeated historical resealing at the first stabilization release

Responsible: Lead and verification writer with separate acceptance by the checker. Sequence: Prepare during stabilization; complete with the first frozen stabilization release that already requires deployed broad acceptance.

**Problem and entry points.** tests/cloud_core_historical_delivery_real_data.py::_retained_applicability checks 663 old source hashes and hard-coded changed/added-file counts; even _run(current_runtime=True) calls it. Its companion requires repeated hash/function/semantic-reach updates. New screenshots alone cannot remove that dependency. Entry points: that module's _cases, _verify, _assert_fixed_runtime, _run; tests/test_core_historical_applicability.py; tests/core1_k08_runtime_binding.py; frontend/tools/captureCoreIdentityFindCount.mjs. [R35] [R59] [R70] [R79] [R87]

**Change.** Preserve the original archive, case manifest and source/receipt identities byte-exact. Bind current acceptance to the actual built deployment, source/runtime/dependency/configuration and intended immutable data. At the justified frozen release, execute the same 22 original question identities on desktop and mobile: 44 actual captures. Preserve independent numerical/sample checks, nonprovisional behavior, pre/post deployment and served-asset binding, screenshot hashes, unique case/viewport coverage and render checks. Separate historical-only verification of its original context
from current-runtime acceptance. Remove the current-runtime dependency on old resealing only after the replacement is independently accepted.

**Verification.** Adapt test_requalify_retained_actual_historical_api_and_ui, test_actual_new_runtime_historical_api_and_ui and test_actual_new_runtime_historical_api_and_ui_on_live_generation deliberately. Retain/extend tests/test_core_historical_applicability.py for tampering, missing/duplicate cases, changed sample, wrong code/data/build and reuse of historical captures as if fresh. The existing full Raw QA, filter sweep, full test suite and deployed release checks still apply once to the frozen candidate.

**Done when.** The current release has equivalent accepted behavioral evidence, original historical evidence still verifies in its original scope, and unrelated new source files no longer force updates to the old per-file bridge. This is an explicit stabilization exit item.

**Boundaries.** No deletion of original proof, changed original numerical oracle, renamed old evidence as fresh, or removal of a guard before equivalent coverage passes. Until replacement is accepted, required existing gates still apply; no massive extra replay solely for cosmetic cleanup.

### W6B - Migrate durable tools before any archive move

Responsible: Agent touching the dependency; lead owns consumer inventory; checker verifies replacement. Sequence: Immediate no-archive protection in W0; actual migrations when a depended-on task path is moved or refactored.

**Problem and entry points.** One hundred source/tool/test/workflow files at the checked baseline reference working/nba-tools-completion-program, including registered publication packages. The default archive policy would otherwise move finished task folders into ignored archive/. [R18] [R36]

**Change.** Inventory actual consumers before moving reusable publishers, preparation tools, fixtures or source oracles. Place durable code and stable contracts in appropriate tracked locations; retain compatibility paths until consumers migrate. Preserve required originals in durable accessible storage. Verify a clean cloud checkout and independent restore with the same inputs before retiring paths. Keep the folder tracked after this finite plan closes if any live consumer still needs it.

**Verification.** Run targeted import/CLI/workflow/schema tests for each moved consumer and the applicable publication/real-data test. Verify clean checkout/restore without an owner laptop, private manual setup or expiring artifact as the only input. Use tests/test_r2_publication_gates.py and the relevant preparation tests when registered paths move.

**Done when.** Every affected consumer resolves its durable replacement; clean checkout/restore succeeds; historical evidence remains recoverable; no archive action removes a required dependency.

**Boundaries.** Do not migrate all task history for tidiness, mirror the git repository into another tracker/storage system or make all 100 consumers a prerequisite to Cleveland. No archive/delete without its actual authority and verified dependencies.

### W7 - Simplify participation meaning at the next relevant change

Responsible: Shared-runtime writer and independent semantic checker. Sequence: First slice is team participation/clause ownership; triggered by its next extension or another defect with the same shared cause.

**Problem and entry points.** natural_query.py reparses/overrides participation meaning across a large dependency surface. Entry points: _team_record_availability_intent, _unresolved_team_record_boundary and their real consumers; _team_appearances.py::{select_appearances,_coverage}; pipeline/team_appearance_coverage.py. Repeated scope fixes make this the concrete first slice. [R28] [R45] [R78]

**Change.** Trace the affected path and introduce one validated representation of primary subject, selected team, condition actors, scope/window, aggregation and output. Use it in the real consumers to reduce repeated parsing and order-dependent overrides. Preserve selected-team appearances, rostered missed games, opponent/anywhere roles, player-stat teammate ownership, ambiguity and unknown coverage.

**Verification.** Use tests/test_team_appearance_scope.py, especially test_global_role_cannot_retarget_or_drop_another_clause, test_scalar_role_keeps_complete_actor_and_numeric_primary_bound, test_negation_cannot_disappear_before_a_scoped_clause and test_pair_checks_unknown_even_when_first_predicate_is_false. Include affected test_team_appearance_scope_real_data.py, test_source_only_participation_names.py and unfamiliar equivalent wording with independently derived results. [R76] [R77]

**Done when.** Equivalent wording preserves meaning; distinct samples stay distinct; no condition disappears; natural/structured answers retain independent values; the changed family has fewer interpretation dependencies.

**Boundaries.** No universal query-language rewrite, file-splitting target or language-model authority to invent NBA values. This is not a blanket Cleveland prerequisite; a confirmed repeated shared defect triggers it instead of another phrase-specific patch.

### W8 - Qualify the next slice and sustainable publication growth

Responsible: Lead plus one bounded data/publication lane and independent checker. Sequence: Before expansion outside the measured model, substantial backfill, recurring publication or wider traffic claims. It gates the applicable Live publication cadence in W9.

**Problem and entry points.** The current candidate is a full 1,461-file, 423,517,896-byte copy; the recorded post-upload bucket projection is 4,048,614,400 bytes against the repository's 10,000,000,000-byte cap. These are recorded figures, not a fresh account inventory. Source completeness and recurring operator effort also constrain league-wide participation. Entry points: generation_publication.py, tools/r2_publication.py, tools/cloud_backup.py, .github/data-publication-packages.json and the existing preparation/coverage pipeline. [R03] [R16] [R17] [R18] [R19]

**Change.** Choose one representative next team/season/source-family slice; reuse held inputs and approved routes. Measure useful complete questions, source calls, preparation/validation time, incremental bytes/objects, serving work, backup/restore size, routine PRs, approval events, owner steps and waiting. Separate one-time architecture repair from recurring cost. The target is reusable tooling and one consolidated publication packet where actual authority permits. Forecast the planned cadence with current meters, retained active/last-good/candidate/history obligations and headroom. If the model requires it, version changed partitions/content and reference unchanged objects through manifests. Preserve old readers and full restoration.

**Verification.** For every applicable expansion, verify complete clean restore, required-object integrity, old-generation compatibility and measured headroom. When content or partition reuse is required or
implemented, demonstrate two releases reusing unchanged objects, correct identity for changed content and restoration of every referenced object into a clean destination. Retain independent answer checks and rollback. Use tests/test_generation_publication.py, test_candidate_generation.py, test_data_source.py and tests/cloud_operations_real_data.py::test_full_generation_backup. Validate source completeness separately from code reuse.

**Done when.** The next useful slice fits the measured acquisition/serving/storage/recovery model and uses the same pipeline without bespoke team code or owner setup. The lead gives one evidence-based recommendation for league-wide progression and raises only a real scope/cost tradeoff.

**Boundaries.** No new source collection is implied by this final-plan task or the currently held checkpoint. No linear forecast from one team, silent unknown-to-absence conversion, automatic deletion, paid service or bulk run. Full reuse migration is mandatory before the planned cadence cannot fit, not before every unrelated Live code change or small publication with demonstrated headroom.

### W9 - Complete current-data delivery and freshness

Responsible: Data/runtime lead and checker; owner for the actual refresh/publication/scope decisions reserved by current rules. Sequence: After the supported Live scope is selected and the applicable W8 storage/operating/recovery gate passes. W3B supplies calendar correctness beforehand.

**Problem and entry points.** Historical cutoffs and candidate previews do not establish current-season usability. The original Live positives, 24-hour freshness requirement and qualified participation meaning remain unfinished. Entry points: ROADMAP.md, acceptance bindings, current-season readiness, existing generation refresh/preparation and protected publication workflow. [R01] [R02] [R03]

**Change.** Implement the complete authorized refresh route: source arrival/capture and as-of times, incremental preparation, exact coverage, duplicates/out-of-order input, late corrections as new immutable versions, partial failure/retry, idempotence, source quotas, quality checks, stale detection, atomic publication and recovery. Match the actual source schedule to the existing freshness requirement. Keep snapshot and Live status distinct until Live conditions genuinely hold.

**Verification.** Verify positive current-season journeys against independent source facts, calendar/timezone boundaries, duplicate and late arrivals, incomplete batches, retry after interruption, stale serving, publication conflict and rollback/restore. Use existing tests/test_generation_refresh.py, season/readiness tests, affected real-data validations and the original requirement ledger. Perform actual deployed acceptance for the claimed scope.

**Done when.** The named current-data experience works with its required freshness, meaning and recovery; original unmet positives actually pass. Full original product completion requires the remaining ledger obligations as well.

**Boundaries.** No unattended collection/publication without actual authority; no daily full-copy publication beyond the approved model; no stale data relabeled Live; no inference of DNP, membership or absence from a missing row. Preserve optional broader product work as its own explicit scope.

## 4. Exact Cleveland release and recovery protocol

### The candidate and the evidence to preserve

| Item | Recorded identity / requirement |
| --- | --- |
| Package | cleveland-team-appearances-2024-v1; candidate availability-cleveland-2024-v3-20261124. [R03] |
| Candidate manifest | d574144512821d202249e1d87926cbbfd053126b7f1e6960582f4a9b52149034 |
| Expected production base | availability-season-inactive-2024-v1-20261116; manifest 0abce6f8261957df6cffc19ce24a4ed408a548e1292a33456ce55c0481903ecc. Re-read actual pointer before preparing and again before writing. |
| Accepted upload | Run 45391469130 / data-publication-45391469130; candidate_independently_verified_not_activated receipt SHA256 b49eed924b26a6c2d5ad0cd0d8c654e37a811a657b8a889548f615c38ebfbd70. Existing prepared publisher 564f2e05 is retained; identify the new reviewed activation implementation separately. |
| Cold qualification | Preview 5986dde5 on reviewed runtime ff0cb12b: 44 games, 31-13, 5.8248 s, first qualified query invocation, empty disk/frame caches and one completed appearance load. Preserve exact receipt and six passed follow-ups. [R05] |
| Actual original budget | At most two fresh preview deployments and eight total preview queries, including the stated six follow-ups. One failed deployment and one successful deployment are recorded. Verify any later explicit grant; do not assume another attempt is authorized. [R25] |
| Required deployed answers | All 87 Cleveland registered deployed_checks at this baseline, plus applicable independent/source/unknown controls. The six preview follow-ups do not replace them. Preserve seven-second pacing and bounded rate-limit retry. [R18] [R17] |

These values identify the reviewed starting point, not permission to ignore a changed live base. A later publication or source/runtime change requires a precise reconciliation. Keep original failed receipts and source identities unchanged.

### Prepare one reviewable owner packet
- Name the reviewed activation workflow/code revision and the exact frozen serving artifact, data candidate and expected base. Include executed independent review/CI and relevant numerical/hosted evidence.
- Show the intended write budget: zero snapshot-object uploads and one guarded pointer update for activation. State the conditional recovery action separately; it is not implicitly authorized by the activation write count.
- Describe the historical-snapshot exception precisely: the actual typed blocker list contains only new_season_not_loaded for the known current-season gap, the intended immutable generation is active, and health, all registered answers and data integrity pass. Strict Live readiness remains false. Include any corresponding monitor alert and snapshot recovery-clock change explicitly.
- Attach or link the exact old-generation recovery evidence, candidate backup-size preflight, post-activation export/restore procedure and approved fallback pair.
- If new protected cold qualification is necessary, finish code preparation first and include the exact artifact, cases, deployment/query budget, success conditions and conditional activation. Existing environment gates remain; one consolidated decision does not mean bypassing a required gate.
- Identify every unresolved item honestly. A conditional approval cannot be used to activate before its qualification conditions pass. No approval is needed merely because a new agent took over an already-authorized scope.

### Backup obligations are concrete and phase-specific

| Phase | Required result |
| --- | --- |
| Before activation: old base | Verify the live base matches the intended last-good generation/manifest. Reconcile retained backup/restore receipts and the durable archive from cloud-backup-44062070685. The release has generation.zip at 66,039,100 bytes, SHA256 dd3361b2f4fb64cbb5b15360d2efe594e9e6fff8c6df0647e5570d9cf76ec786. Its exact-generation request and successful separate-runner restore are verified. Reuse valid proof; re-export only if missing, mismatching or invalidated. [R54] [R55] [R56] |
| Before activation: candidate | Check exact candidate inventory and prospective backup/restore against current limits: 3,000 files, 1,000,000,000 uncompressed bytes and 200,000,000 compressed archive bytes. Prove compressed size from the exact retained/reconstructed candidate, not a sampled ratio. If needed, add a bounded read-only candidate preflight; current export_backup reads active data and is not silently repointed. No second R2 snapshot upload. [R19] |
| Before activation: recovery | Record the last-good app deployment plus data pair and the intended prospective rollback target. Validate the target and its evidence using an explicitly read-only client/path. rollback_r2_generation has no dry-run flag and writes: do not call it to simulate a read-only rehearsal. [R16] |
| After activation | Verify candidate.previous is the approved base; verify every required object and answer. Extend the existing publication hook to export the newly active candidate, retain it durably, and perform a separate credential-free full restore including the real loader. Retain its independent restore receipt. Delivery remains incomplete until this passes. [R50] [R57] [R63] [R66] |
| Separate dependable-production milestone | Daily independent backups, sustained RPO, separate-account/disaster exercises and Live refresh remain their own requirements. They are not new Cleveland prerequisites. The required candidate export/restore above remains mandatory. [R57] |

The final review confirmed release metadata, the exact-generation request and successful backup/restore workflow steps. It did not download/revalidate the entire old archive or run a new restore. Execution preflight reconciles the retained receipt/manifest identities and availability before reuse.

### Release states and permitted next actions

| Observed state | Next action | Claim allowed |
| --- | --- | --- |
| Prepared, not approved | Complete the exact packet and required preflight. Keep independent work moving. | Technically prepared; nothing activated. |
| Approved, pre-write | Recheck actual main/review/CI requirements, authority, expected base, candidate bytes and applicable qualification. | Authorized for the specific bounded action. |
| Write attempted, result uncertain | Read pointer, manifest and durable receipt. Classify base unchanged, intended candidate active or a later/conflicting publication. No blind retry or reupload. | Outcome unresolved until reconciled. |
| Candidate active | Confirm candidate/base linkage, independent data integrity and every registered answer; complete candidate export/restore. | Active; not yet delivered. |
| Verification or backup fails | Record exact failure and actual app/data identity. Use only the approved recovery condition; otherwise preserve state and prepare the smallest valid repair/recovery action. | Delivery incomplete; no fabricated success. |
| Recovery approved and needed | Assert current active is still the failed candidate and target is the approved base before conditional write. Recover the app too if the failure requires its last-good pairing. | Recovery attempted; verify resulting pair. |
| Recovery verified | Run required known answers/data/recovery checks against the restored pairing; retain failed-candidate evidence. | Last-good service restored; failed candidate unaccepted. |
| All release conditions pass | Update the single queue and public capability status with the accepted runtime/data identity. | Cleveland delivered; full/Live scope remains separate. |

A normal compare-and-swap protects against a concurrent pointer change, but a recovery wrapper must also reject a newer publication that was already active when it began. Do not call the existing rollback writer without that intended-candidate/target guard.

Snapshot verification must validate the complete readiness schema. Do not classify success from a filtered safe-log list that could have silently omitted malformed blockers. A known gap cannot mask extra blockers, generation drift, unavailable object bodies, wrong answers or unexpected HTTP responses.

If a protected operation is delayed, the lead records that exact state and continues independent authorized work on branches. Source reacquisition, duplicate uploads, repeated whole-project reviews and unrelated changes to the frozen artifact are not fallback activities.

## 5. Verification, measurement and growth decisions

### What evidence each result must establish

| Result | Required interpretation |
| --- | --- |
| Numerical correctness | Expected NBA values and game/sample identities come from qualified source rows or independent controlled fixtures. Two engine paths agreeing is not sufficient. |
| Artifact applicability | Identify code, actual built deployment, interpreter/dependency inputs, relevant configuration and immutable data. Record unknown historical input information rather than inventing equality. |
| Cleveland cold | The exact accepted <=20 s gate, original first-query/cache/appearance indicators and actual remaining authority apply. Reuse applicable evidence without claiming a new run. |
| General K12 | S1 summary, R1 record, B1 ranking, M1 comparison and H1 historical keep their existing scope. The binding records eight controlled common cold observations and forty warm, plus two cold and ten warm historical observations. Controlled process-cold and real deployed-cold are separate claims; use the existing case/control and sample contract. [R04] |
| Complete request cost | Measure external elapsed time, initialization/processing/serialization, fetched objects/bytes, scanned rows, peak and incremental memory, active jobs and disk/cache lifecycle. One fast response does not establish a percentile or total capacity. |
| Concurrency | Three same-worker admitted requests must succeed for the current design. Excess 429 behavior is separate. A lower worker limit is an evaluated alternative, not proof that rejected work will be routed elsewhere. |
| Release acceptance | Existing full Raw QA, filter sweep, full suite and deployed desktop/mobile obligations run once for the frozen release; affected exact-head checks and independent review remain. W6A reuses this justified release, preserving the 22-question/44-capture historical contract. |
| Operational reliability | Prove real workflow and scheduled execution, classification and failure action. Preserve the existing rolling 30-day 99% monitoring objective and scheduled-coverage reporting; at complete normal coverage its threshold is 357/360. Do not rewrite historical failures or equate scheduling gaps with uptime. [R58] [R83] |

Current public platform documentation supports Python lock inputs and distinguishes platform resource/response limits, but it is not account telemetry. Use actual deployment evidence for this project. The observed memory-setting warning makes the configured 1024 value insufficient as a worker-capacity claim. [R07] [R08] [R39] [R40]

### Storage pressure is a quantified trigger

Using only the recorded candidate increment and policy cap, (10,000,000,000 - 4,048,614,400) / 423,517,896 is about 14 additional equal-sized copies. Daily full copies would use that illustrative headroom in about two weeks. This is a stress illustration, not a live forecast: current usage, other candidates, retention, backup/restore space and growing data alter the result. Do not make a cost or capacity promise from it. [R03] [R18]

Before the next planned material expansion or recurring update, W8 reconciles current relevant meters and the intended cadence. Reuse unchanged objects before that plan would exceed its approved storage/restore model. Protect objects reachable from the active and last-good releases, approved candidates, in-flight readers and retained evidence/restore obligations. Define and authorize deletion before performing it. A clean restore must retrieve every referenced object, including those reused from older releases.

W8's operating qualification is a hard predecessor of recurring/bulk Live publication in W9. Calendar repairs and independent Live code preparation may proceed without a speculative storage migration. A small publication with demonstrated safe headroom does not acquire an unrelated migration prerequisite.

### How the lead resolves a failed task

| Failure or uncertainty | Required decision / stop condition |
| --- | --- |
| Known wrong answer or integrity loss | Contain the affected path with explicit unavailable/error behavior; repair the shared cause and run focused independent proof. Do not treat that containment as feature completion. |
| Supported workload exceeds limits | First remove avoidable amplification. Compare one measured alternative, including admission/caching/format or hosting if relevant, with actual user, resource and cost consequences. No indefinite tuning or silent requirement reduction. |
| Missing or exhausted source route | Name the exact missing fact and concrete untried route or unblocking event. Preserve unknowns and move to independent work. No repeat investigation without new evidence. |
| Account telemetry unavailable | State exactly which resource/cost claim is unverified. Continue independent code and evidence work; optional access troubleshooting is not a project-wide stop. |
| New artifact requires new protected proof | Freeze the exact artifact and prepare the bounded qualification request, retaining applicable old source evidence. Do not spend an old budget again by changing its label. |
| Policy or protected setting decision | Finish the reviewable implementation/configuration and evidence first. Bring one recommendation and exact reserved action, reusing existing authorization where applicable. |
| New discovery during stabilization | Include it only if it affects current correctness, mandatory release safety or the defined exit. Otherwise give it a responsible role and concrete trigger in this plan/checkpoint. |

Relative size: W0 and run-all monitoring are focused changes; W1/W2 are substantive correctness/delivery work; W5 and W6A require careful integration; W3 size depends on measurements; W8/W9 are later growth milestones. The lead reports completed outcomes, observed active work and real waiting separately. PR count and invented dates are not progress measures.

## 6. Completion and first execution assignment

### Cleveland is delivered when all four conditions hold
- The intended candidate is active through the protected route under actual authority, with the exact expected-base/candidate relationship independently confirmed.
- Every mandatory registered deployed answer/control and required data-integrity check passes for the accepted runtime/data pair. The website can obtain the intended capability.
- The candidate has its required durable byte-exact export and independent credential-free full restore; the last-good app/data path remains usable.
- The queue and public scope accurately record delivery and the separate unresolved current-season/Live requirement.

### Snapshot stabilization ends when these outcomes hold
- W1 closes mixed-version identity and silent required-object failures with focused consumer proof, real-data checks and independent review.
- W3A bounds input, limiter state, active work and deadlines; W3B corrects request-clock and explicit calendar scope while preserving snapshot/default meanings.
- W5 binds the production-equivalent build. W3C final evidence passes for the coherent frozen artifact across its named supported workload, admitted concurrency, operating bounds, eviction and failure cases. Missing or failed proof for those required outcomes keeps stabilization open. Only separately parked broader K12 claims or optional telemetry beyond the explicitly qualified operating range may remain recorded as open; they cannot support a claimed capacity guarantee.
- W4A monitoring runs the historical query independently of the known Live gap, under the correct approved classification, with actual workflow/scheduled evidence and real ownership.
- W4B fresh desktop/mobile discovery, correct scoped answers and useful error recovery pass; misleading current/unverified examples are replaced.
- W6A replaces the current-runtime dependency on the old historical resealing bridge with independently accepted equivalent current evidence; original evidence remains intact.
- W0 leaves one self-contained current contract and queue, and W6B archive protection remains in force until its consumers migrate.
- Every remaining item below has its actual trigger and acceptance. Pending optional reserved settings are named accurately and do not keep otherwise completed stabilization open.

An unresolved condition that prevents a required claim keeps that specific claim open. If only protected publication is pending, technical readiness and public delivery are reported separately. Missing optional telemetry does not halt unrelated work. There is no automatic seven-day calendar hold: verify the repair, confirm scheduled execution and continue observing under the existing monitoring objective while useful work proceeds.

Once these outcomes hold, end stabilization and resume the next capability from the original requirement ledger within standing authority. Do not turn this finite correction into an unlimited cleanup program.

### Remaining work has explicit return points

| Item | Trigger / responsible role / required result |
| --- | --- |
| W6B durable tool migration | Before moving or archiving any depended-on path. Touching agent plus lead: complete consumer migration and clean checkout/restore. Until then, keep it tracked. |
| W7 participation representation | Next relevant participation extension or shared-cause defect. Runtime writer/checker: preserved independent meaning with reduced duplicate interpretation. |
| W8 source and storage economics | Before material expansion, recurring publication or a broader capacity promise. Lead/data lane: representative useful coverage, recurring operator effort, headroom and complete restore. |
| Retention/deletion | Before planned retention would exceed the measured envelope. Lead prepares policy/reachability/recovery; owner decides actual deletion where reserved. |
| W9 Live operation | At the authorized current-data milestone after applicable W8 gates. Data/runtime lead: positive Live journeys, 24-hour freshness, corrections, atomic publication and recovery. |
| Required-check settings | When the concrete reserved setting is authorized or collaboration/access changes require it. Lead: effective checks and workable solo-owner integration; no invented second human reviewer. |
| Wider traffic and abuse controls | Before use expands beyond measured conditions. Lead: actual admission/global-budget, abuse and failure evidence; a process-local limiter is not an account-wide control. |

### The first implementation assignment

Goal: carry the existing NBA Tools candidate to verified Cleveland delivery, then complete the finite stabilization program in this plan.

Start: check current main, open work and the Resume checkpoint. Reconcile deltas from main 718d4ac5 without restarting the audit. Preserve the historical blocked PR 462, the saved unreviewed Tatum branch and existing parked/source restrictions. Adopt W0 in the tracked working plan; protect the load-bearing folder. Confirm the actual delivery route before claiming the adoption will not build.

Lead with delivery: collect W5A build/data identity read-only; restore W4A run-all monitoring; implement W2's protected activation/verifier/backup/recovery path. Preserve strict verdicts until any policy change has its actual authority. Form the minimum pre-activation operational release and freeze it. Reuse the qualified upload and applicable cold evidence; if new proof is actually needed, prepare one bounded concrete packet rather than resetting the consumed budget.

Parallel lane: W1 may be authored/reviewed independently while delivery preparation proceeds. Merge it after Cleveland acceptance unless an independently demonstrated relevant defect requires it earlier. Keep all other deployment-affecting changes outside the frozen release.

Finish: after authorized activation, complete all registered checks and candidate export/restore. Then integrate W1, W3A/W3B, W5 and W4B; prepare W6A; freeze the stabilization artifact and run W3C and required release acceptance once. End the phase using the conditions above. Return only a real
unresolved owner decision after making it concrete, and continue independent authorized work while waiting.

Closeout format: useful capability now available; exact unfinished scope; what was actually verified; next action; a genuine owner action only if required. Distinguish technically ready, active/unverified, delivered and stabilized. Preserve one next action at an actual stop.

## Appendix A. Findings and closure map

This appendix is sufficient to interpret F1-F15 without access to the original audit. Code locations are pinned through the source links. The lead owns the entire map; a finding is closed by its stated evidence or remains assigned to a named trigger.

| Finding and evidence entry | Failure / reproducible observation | Assigned closure |
| --- | --- | --- |
| F1 - Prepared serving R2 reader and qualified appearance path. [R05] [R14] [R45] | The old path downloaded/replayed original source proof during interactive serving and failed hosted cold qualification. PR 643 now serves verified prepared objects. Verify consumed-object integrity without source replay. | W2 preserves the repaired path; W3C checks other costly routes; W8 uses prepared facts for new slices. Original qualification remains at preparation time. |
| F2 - Version-safe identity entity_resolution.py::_ensure_player_index_generation / reset_player_index. [R09] | Module-level indexes share a single generation key and reset nonatomically. Interleave old/new requests with an added same-name player to expose identity or spelling contamination. | W1 immutable coalesced per-generation bundle retained by each request; old/new overlap and failed construction tests pass. |
| F3 - Required-object integrity _read_player_names / _read_published_player_names. [R09] [R15] | Broad catches hide required ledger/season failures. Combine a missing ledger with a failed season to test whether ambiguity disappears into a plausible partial answer. | W1 errors propagate through real consumers. Only explicit optional legacy absence permits a verified complete fallback; corrupt required bytes remain errors. |
| F4 - Protected release path publication workflow/registry/CLI and verify_published_snapshot. [R17] [R18] [R50] | Activation exists below the public tooling but is not exposed. Strict ready=true verification blocks registered snapshot answers while Live is unavailable. | W2 guarded pointer-only activation, exact scoped policy decision, all 87 registered controls, uncertain-outcome reconciliation and new-candidate export/restore. |
| F5 - Resource envelope admission_control.py, data_utils.py, data_source.py, dataframe_cache.py. [R11] [R12] [R14] [R47] | Caches and a concurrency limit do not prove full-request memory, disk, latency or three admitted successes across costly history and rollover. | W3C named complete-request workload and measured limits after build freeze; bounded storage/active work with preserved correct answers. |
| F6 - Monitoring coverage production_monitoring.py::run_production_monitor; scheduled workflow. [R10] [R53] [R83] | Readiness failure breaks the loop before the representative query. Latest reviewed run confirms health passes and query is omitted. Monitoring gap is not measured website downtime. | W4A before activation: all checks run, typed exact known gap remains visible, unexpected snapshot failures are actionable; scoped policy/RTO change approved where required. |

| Finding and evidence entry | Failure / reproducible observation | Assigned closure |
| --- | --- | --- |
| F7 - Storage growth generation_publication.py; publication registry; cloud_backup.py. [R16] [R18] [R19] | Full immutable copies repeat unchanged content. Recorded candidate 423.5 MB and projected 4.049 GB show why recurring versions need an explicit growth/restore model. | W8 before planned cadence exceeds the measured model: reuse unchanged content, protect reachability, verify old readers and full clean restore; retention authority explicit. |
| F8 - Effective platform/cost limits vercel.json versus actual deployment evidence. [R07] [R08] [R39] | Configured memory is explicitly ignored in reviewed build logs. Generic provider limits, repo policy caps and live account usage are different facts. | W3C measures current demand/effective limits; W8 measures planned growth meters. Unavailable telemetry leaves a specific claim open, never an invented capacity/cost promise. |
| F9 - Repeatable dependencies pyproject.toml, CI and R2 install paths. [R20] [R21] [R80] | Broad package ranges and differing interpreter contexts allow fresh resolution; build logs do not expose a full installed graph. | W5 actual input capture plus deployed lock consumption and aligned production-equivalent jobs; affected qualification follows that build. |
| F10 - Merge/build controls delivery_scope.mjs and actual required checks. [R22] [R23] [R24] | docs/ paths select full work; unknown first-branch build history conservatively builds. A merge-base or a docs suffix cannot prove unbuilt changes are absent. | W0 uses the correct task location and actual route; W5 proves safe selection and obeys CI/review. Reserved branch-setting proposal stays explicit. |
| F11 - Query interpretation coupling natural_query.py participation routing/overrides. [R28] [R76] | Repeated interpretation and order-dependent overrides risk losing team/actor/condition scope. Equivalent and negated clause tests expose the boundary. | W7 starts with team participation at the next relevant extension/shared-cause defect; one validated meaning used by real consumers. |
| F12 - Rules, tools and historical evidence AGENTS; working/ consumers; historical applicability verifier. [R01] [R35] [R36] [R59] | Hidden prior-rule inheritance, 100 operational path consumers and a current-runtime test that reseals old source hashes create fragility and repeated work. | W0 self-contained contract/archive guard; W6A replaces current historical resealing at first stabilization RC; W6B migrates consumers before any archive move. |
| F13 - Honest scope and discovery SampleQueries.tsx and frontend error/result flows. [R31] [R32] [R33] | Literal-current/unverified starters and weak error handling can promise unavailable capability or hide useful failure information. | W4B verifies actual examples and covered windows; fresh desktop/mobile discovery/answer/error journey passes with clear scope. |
| F14 - Calendar meaning _seasons.today; import-time CURRENT_QUERY_DATE; cutoff anchoring. [R28] [R30] [R71] | Two clocks disagree across timezone/midnight; stale data can replace the literal requested calendar interval. A clock-only patch is insufficient. | W3B fixes clock lifecycle and literal scope now; W4B labels snapshot behavior; W9 later supplies positive Live data/freshness. Defaults and last-N-game meanings remain intact. |
| F15 - Bounded input, errors and privacy JsonHandler, AdmissionController and frontend client. [R12] [R13] [R32] [R34] | Body is read before its size check, old limiter keys accumulate, and equal internal/host deadlines can pre-empt useful errors. Frontend must retain status/retry/request identity. | W3A bounds reads/keys/deadlines and active work; W4B preserves structured errors and stale-response suppression. Safe logs and disabled public feedback persistence remain. |

## Appendix B. Disposition of the additional review

The additional review correctly challenged the execution detail and sequencing. The decisions below resolve its recommendations; they are not a second backlog. Factual corrections were checked against the repository and live release/deployment evidence. [R52]

| Review recommendation | Final decision and reason |
| --- | --- |
| Monitor first; fix snapshot recovery clock | Accepted. W4A precedes activation. Run all checks first; preserve strict Live status. Scope alert/publication/recovery policy changes in the actual owner packet. Lost query coverage does not prove a continuous service outage. |
| Make Cleveland the lead; hold query merges | Accepted and widened. W2 leads; W1 normally lands afterward. The freeze covers every production-rebuilding input, including frontend, tooling and monitoring. Necessary operational changes receive one applicability/qualification decision. |
| Compare installed-package lists to transfer cold proof | Qualified. The retrieved build logs lack those lists. Equality alone would also be insufficient: code/artifact/config/data/test conditions matter. W5 captures actual inputs and preserves honest unknowns. |
| Treat verifier exception as a concrete owner decision | Accepted, with monitor alert/recovery semantics and conditional recovery included where those change approved safeguards. Preparation proceeds first; existing applicable authority is reused. |
| Only the October backup exists | Corrected. A November 17 durable backup and successful independent restore cover the active generation. W2 preflight reconciles/reuses them. [R54] [R55] [R56] |
| Old-base backup + retained pointer + rollback dry-run is enough | Corrected. Existing obligations also require a new-candidate backup and independent restore after activation. The current rollback function always writes; W2 specifies a truly read-only preflight and guarded recovery. Daily/disaster E-03B remains separate. |
| Put W0 in working/; separate rules/runbooks/history | Accepted. The active plan and self-contained findings live in the tracked working folder. Canonical locations are explicit. A first branch can still build, so no path-only no-deployment promise is made. |
| Protect task folder; remove named current lead from durable plan | Accepted. Archive protection is immediate and dependency-based; the checkpoint names the current lead. |
| Retire historical resealing at first stabilization release | Accepted and strengthened. W6A replaces the current-runtime dependency, not just the captures. Preserve original archive/receipts and independently qualify the same 22 identities across 44 viewport captures with equivalent guards. |
| Bundle body/limiter/deadline fixes; use 16-17 seconds | Repairs accepted in W3A; guessed timeout rejected. The correct margin is measured against effective host and full-response costs. Changes remain coherent units rather than a mandated single PR. |
| Unify clocks now; leave calendar meaning later | Refined. W3B fixes both request clocks and already-defined literal calendar scope during stabilization. Preserve snapshot defaults and last-game meanings; unavailable literal-current answers do not pass Live positives. |

| Review recommendation | Final decision and reason |
| --- | --- |
| Change all starters to 2025-26; frontend can ship anytime | Qualified. W4B uses individually verified questions/windows, not a blanket year replacement. Frontend builds respect the same Cleveland artifact freeze. |
| Use cold marker to close K12 | Accepted as a bounded verification route, not automatic closure. The actual header is X-NBATools-Candidate-Qualification; its class is ColdQualification. Adapt its appearance-specific checks and satisfy K12 scope, timing, equivalence and authority. |
| Reduce per-instance concurrency because the host scales | Retained as a measured alternative. A process-local 429 is not proven to be rerouted. Preserve the current three-admitted-success target unless an explicitly evaluated service change is accepted. |
| Lock dependencies early; use merge-base for first push | Early capture/locking accepted. Merge-base alone rejected: require an actually built equivalent base or a safe reviewed trigger, including unbuilt-code and environment-redeploy guards. |
| Make W8 precede every new publication and all Live work | Refined. A storage/operating/recovery gate precedes material expansion and recurring/bulk Live publication. Full content reuse must precede a cadence that cannot fit; unrelated code or a proven small publication need not wait for a speculative migration. |
| Track PRs/approvals per team-season; name W7 first slice | Accepted with context. W8 separates one-time repair from recurring cost and supports the settled league-wide goal. W7 first addresses team participation/clause ownership. Owner input is for an actual tradeoff. |
| Remove repeated history/rules; add files/tests/done/exclusions | Accepted. Fixed-format work packages, canonical repository homes, self-contained F1-F15 and this compact disposition replace the old history table and parallel rule copies. |
| List owner gates; estimate 12-18 PRs; reduce paperwork | Owner gate triggers and evidence-in-work-PR rule accepted. An unsupported PR-count commitment is omitted; relative size and measurement uncertainty are stated instead. |
| Seven consecutive green days as stabilization gate | Not adopted as a new hard gate. Confirm failure handling and real scheduled execution, then observe while useful work proceeds. Preserve the existing rolling 30-day objective; seven days does not establish it. |
| Memory/duration changes cost money; all other config edits ordinary | Corrected. Authority follows actual effect: resource/settings/access/protection/cost changes remain reserved. A config edit does not automatically incur charges or automatically grant permission. |

## Sources and evidence

Repository links are pinned to reviewed main 718d4ac5877df2051e29fbdd2b610f8724dafb35 unless another revision is explicitly named. Live deployment/run/release links identify the evidence inspected. The source PDFs are provenance; Appendix A and the work packages contain the execution facts needed without private document access. All implementation remains subject to the short live-state reconciliation at entry.

- R01 — [Current project instructions](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/AGENTS.md)
- R02 — [Roadmap and completion criteria](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/ROADMAP.md)
- R03 — [Current queue, qualified candidate and remaining scope](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/working/nba-tools-completion-program/README.md)
- R04 — [K12 latency budgets and earlier performance evidence](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/working/nba-tools-completion-program/k12-binding.md)
- R05 — [PR 643: repair, independent review, hosted result and production receipt](https://github.com/Bet-Zero/nbatools/pull/643)
- R07 — [Production deployment: READY, merge 718d4ac5, stable alias](https://vercel.com/zeros-projects-686e97fc/nbatools/VGmn1JWbDGRWYMj9PMEMpxaaya7f)
- R08 — [Candidate deployment and runtime/build logs](https://vercel.com/zeros-projects-686e97fc/nbatools/2eQNvuDvCrnqUNebDxHWG9e6REYT)
- R09 — [Player-name resolution and mutable indexes](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/commands/entity_resolution.py)
- R10 — [Production monitor and early-stop behavior](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/production_monitoring.py)
- R11 — [Data loading and historical frame retention](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/commands/data_utils.py)
- R12 — [Admission, request limits and timeout accounting](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/admission_control.py)
- R13 — [Vercel HTTP body handling](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/vercel_http.py)
- R14 — [R2 reader and generation caches](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/data_source.py)
- R15 — [Verified reader after the merged repair](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/data_source.py)
- R16 — [Immutable generation publication](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/commands/pipeline/generation_publication.py)
- R17 — [Publication size preflight](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tools/r2_publication.py)
- R18 — [Registered packages and storage caps](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/.github/data-publication-packages.json)
- R19 — [Cloud backup limits and restore support](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tools/cloud_backup.py)
- R20 — [Python dependency declarations](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/pyproject.toml)
- R21 — [CI matrix and dependency installation](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/.github/workflows/ci.yml)
- R22 — [Main branch enforcement state, live API](https://api.github.com/repos/Bet-Zero/nbatools/branches/main)
- R23 — [Repository rulesets, live API](https://api.github.com/repos/Bet-Zero/nbatools/rulesets)
- R24 — [Deployment selection logic](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tools/delivery_scope.mjs)
- R25 — [Deployment and publication runbook](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/docs/operations/deployment.md)
- R28 — [Natural-query parsing, route overrides and date anchoring](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/commands/natural_query.py)
- R29 — [Query service and result handling](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/query_service.py)
- R30 — [Date helpers and import-time clock](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/commands/_date_utils.py)
- R31 — [Public starter queries](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/frontend/src/components/SampleQueries.tsx)
- R32 — [Frontend API error handling](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/frontend/src/api/client.ts)
- R33 — [Frontend request ownership and cancellation](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/frontend/src/App.tsx)
- R34 — [Safe operational logging](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/operational_observability.py)
- R35 — [Historical evidence applicability bridge](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/cloud_core_historical_delivery_real_data.py)
- R36 — [Working and archive lifecycle policy](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/docs/operations/working_and_archive_policy.md)
- R37 — [Contribution and verification rules](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/CONTRIBUTING.md)
- R39 — [Vercel function limits, official documentation](https://vercel.com/docs/functions/limitations)
- R40 — [Vercel Python runtime and lockfile support, official documentation](https://vercel.com/docs/functions/runtimes/python)
- R45 — [Participation observation construction](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/commands/_participation_observations.py)
- R47 — [Bounded DataFrame cache](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/dataframe_cache.py)
- R49 — [Cleveland preparation and exact-delta preservation contract](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/working/nba-tools-completion-program/prepare-cleveland-candidate.py)
- R50 — [Protected publication workflow and exposed operations](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/.github/workflows/r2-data-publication.yml)
- R51 — [Original architecture review (historical evidence)](https://chatgpt.com/library?file_id=libfile_fde3_f-70282316b3e8819198350aa2e8000d11_02d8c7b50e448191a57acf07ae6018a2&account_id=personal)
- R52 — [Claude final-pass review supplied by the owner](https://chatgpt.com/library?file_id=libfile_fde3_f-c5d3ce55c2488191b91695a6f1a03361_02d8c7b50e448191a57acf07ae6018a2&account_id=personal)
- R53 — [Reviewed failed production monitor run, 25 November](https://github.com/Bet-Zero/nbatools/actions/runs/45594140692)
- R54 — [Durable current-generation backup release, 17 November](https://github.com/Bet-Zero/nbatools/releases/tag/cloud-backup-44062070685)
- R55 — [Successful export and independent restore workflow](https://github.com/Bet-Zero/nbatools/actions/runs/44062070685)
- R56 — [Exact active-generation backup request](https://github.com/Bet-Zero/nbatools/blob/f84afe17d89405382c12253f6ea4a46952072844/.github/r2-validation-request.json)
- R57 — [Recovery runbook and backup obligations](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/docs/operations/recovery.md)
- R58 — [Approved monitoring policy and recovery objectives](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/docs/operations/observability.md)
- R59 — [Historical evidence binding and companion](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/working/nba-tools-completion-program/source-evidence/core-live-current-20261107/historical-applicability-20261110.json)
- R60 — [Production monitor tests](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_production_monitoring.py)
- R61 — [Production monitor workflow tests](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_production_monitor_workflow.py)
- R62 — [Candidate activation and cold-proof tests](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_candidate_generation.py)
- R63 — [Protected publication gate tests](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_r2_publication_gates.py)
- R64 — [Publication real-data tests](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_r2_publication_real_data.py)
- R65 — [Generation publication and recovery tests](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_generation_publication.py)
- R66 — [Full-generation export and restore real-data entry](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/cloud_operations_real_data.py)
- R67 — [Admission and request-budget tests](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_admission_control.py)
- R68 — [Production adapter and bundle tests](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_vercel_functions.py)
- R69 — [Delivery selection guard tests](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_delivery_scope.py)
- R70 — [Historical applicability guard tests](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_core_historical_applicability.py)
- R71 — [Season clock helpers](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/commands/_seasons.py)
- R72 — [Season rollover tests](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_season_rollover.py)
- R73 — [Protected-preview cold instrumentation](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/candidate_preview.py)
- R74 — [K12 real-data acceptance](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_k12_delivery_real_data.py)
- R75 — [K12 deployed browser acceptance](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_deployed_k12_delivery_browser.py)
- R76 — [Participation meaning and clause-scope tests](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_team_appearance_scope.py)
- R77 — [Participation real-data tests](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_team_appearance_scope_real_data.py)
- R78 — [Snapshot appearance selection](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/commands/_team_appearances.py)
- R79 — [Current source binding for historical captures](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/working/nba-tools-completion-program/source-evidence/core-live-current-20261107/live-code-binding.json)
- R80 — [Existing authenticated validation and backup workflow](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/.github/workflows/r2-real-data-validation.yml)
- R81 — [Prior instructions to reconcile once, without erasing safeguards](https://github.com/Bet-Zero/nbatools/blob/95cb705/AGENTS.md)
- R82 — [Separate read-only publication verification](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/.github/workflows/r2-publication-readonly.yml)
- R83 — [Existing scheduled production monitor](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/.github/workflows/production-monitor.yml)
- R85 — [Natural date query tests](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_natural_date_queries.py)
- R86 — [Explicit date-range tests](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_explicit_date_ranges.py)
- R87 — [Current deployed-evidence capture tool](https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/frontend/tools/captureCoreIdentityFindCount.mjs)

[R01]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/AGENTS.md
[R02]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/ROADMAP.md
[R03]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/working/nba-tools-completion-program/README.md
[R04]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/working/nba-tools-completion-program/k12-binding.md
[R05]: https://github.com/Bet-Zero/nbatools/pull/643
[R07]: https://vercel.com/zeros-projects-686e97fc/nbatools/VGmn1JWbDGRWYMj9PMEMpxaaya7f
[R08]: https://vercel.com/zeros-projects-686e97fc/nbatools/2eQNvuDvCrnqUNebDxHWG9e6REYT
[R09]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/commands/entity_resolution.py
[R10]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/production_monitoring.py
[R11]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/commands/data_utils.py
[R12]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/admission_control.py
[R13]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/vercel_http.py
[R14]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/data_source.py
[R15]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/data_source.py
[R16]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/commands/pipeline/generation_publication.py
[R17]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tools/r2_publication.py
[R18]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/.github/data-publication-packages.json
[R19]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tools/cloud_backup.py
[R20]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/pyproject.toml
[R21]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/.github/workflows/ci.yml
[R22]: https://api.github.com/repos/Bet-Zero/nbatools/branches/main
[R23]: https://api.github.com/repos/Bet-Zero/nbatools/rulesets
[R24]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tools/delivery_scope.mjs
[R25]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/docs/operations/deployment.md
[R28]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/commands/natural_query.py
[R29]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/query_service.py
[R30]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/commands/_date_utils.py
[R31]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/frontend/src/components/SampleQueries.tsx
[R32]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/frontend/src/api/client.ts
[R33]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/frontend/src/App.tsx
[R34]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/operational_observability.py
[R35]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/cloud_core_historical_delivery_real_data.py
[R36]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/docs/operations/working_and_archive_policy.md
[R37]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/CONTRIBUTING.md
[R39]: https://vercel.com/docs/functions/limitations
[R40]: https://vercel.com/docs/functions/runtimes/python
[R45]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/commands/_participation_observations.py
[R47]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/dataframe_cache.py
[R49]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/working/nba-tools-completion-program/prepare-cleveland-candidate.py
[R50]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/.github/workflows/r2-data-publication.yml
[R51]: https://chatgpt.com/library?file_id=libfile_fde3_f-70282316b3e8819198350aa2e8000d11_02d8c7b50e448191a57acf07ae6018a2&account_id=personal
[R52]: https://chatgpt.com/library?file_id=libfile_fde3_f-c5d3ce55c2488191b91695a6f1a03361_02d8c7b50e448191a57acf07ae6018a2&account_id=personal
[R53]: https://github.com/Bet-Zero/nbatools/actions/runs/45594140692
[R54]: https://github.com/Bet-Zero/nbatools/releases/tag/cloud-backup-44062070685
[R55]: https://github.com/Bet-Zero/nbatools/actions/runs/44062070685
[R56]: https://github.com/Bet-Zero/nbatools/blob/f84afe17d89405382c12253f6ea4a46952072844/.github/r2-validation-request.json
[R57]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/docs/operations/recovery.md
[R58]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/docs/operations/observability.md
[R59]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/working/nba-tools-completion-program/source-evidence/core-live-current-20261107/historical-applicability-20261110.json
[R60]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_production_monitoring.py
[R61]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_production_monitor_workflow.py
[R62]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_candidate_generation.py
[R63]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_r2_publication_gates.py
[R64]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_r2_publication_real_data.py
[R65]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_generation_publication.py
[R66]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/cloud_operations_real_data.py
[R67]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_admission_control.py
[R68]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_vercel_functions.py
[R69]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_delivery_scope.py
[R70]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_core_historical_applicability.py
[R71]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/commands/_seasons.py
[R72]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_season_rollover.py
[R73]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/candidate_preview.py
[R74]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_k12_delivery_real_data.py
[R75]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_deployed_k12_delivery_browser.py
[R76]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_team_appearance_scope.py
[R77]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_team_appearance_scope_real_data.py
[R78]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/src/nbatools/commands/_team_appearances.py
[R79]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/working/nba-tools-completion-program/source-evidence/core-live-current-20261107/live-code-binding.json
[R80]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/.github/workflows/r2-real-data-validation.yml
[R81]: https://github.com/Bet-Zero/nbatools/blob/95cb705/AGENTS.md
[R82]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/.github/workflows/r2-publication-readonly.yml
[R83]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/.github/workflows/production-monitor.yml
[R85]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_natural_date_queries.py
[R86]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/tests/test_explicit_date_ranges.py
[R87]: https://github.com/Bet-Zero/nbatools/blob/718d4ac5877df2051e29fbdd2b610f8724dafb35/frontend/tools/captureCoreIdentityFindCount.mjs
