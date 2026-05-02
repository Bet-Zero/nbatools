# Phase N3 Work Queue

> **Role:** Sequenced, PR-sized work items for Phase N3 of
> [`production_deployment_plan.md`](./production_deployment_plan.md) -
> _Monitoring, deployed freshness evidence, and stability._
>
> **Deployment target rule:** Until the developer buys or chooses the custom
> domain from Phase N2 item 4, use the active Vercel deployment URL as the
> deployment target for this phase. As of 2026-05-02, the verified deployed
> UI target is
> `https://nbatools-kn8wz220h-brents-projects-686e97fc.vercel.app/`.
> Anything that genuinely requires the custom domain stays deferred to Phase
> N4 wrap-up.
>
> **How to work this file:** Find the first unchecked item below. Review the
> reference docs it cites. Execute per its acceptance criteria. Run the test
> commands. Check the item off, commit, open a PR, wait for CI, merge when
> green, then continue to the next unchecked item unless the item is explicitly
> human-gated or a real blocker appears.

---

## Status legend

- `[ ]` - not started
- `[~]` - in progress
- `[x]` - complete and merged
- `[-]` - skipped (with inline note explaining why)

---

## 1. `[x]` Audit the deployed monitoring/freshness surface and lock the N3 evidence workflow - completed on 2026-05-02: `phase_n3_monitoring_inventory.md` locks the active deployment-target rule, canonical smoke cases, evidence artifacts, and the custom-domain checks deferred to Phase N4.

**Why:** N3 needs a domain-agnostic monitoring plan anchored on the actual
deployed surface, not on the still-missing custom domain.

**Scope:**

- Review the current deployed URL, Phase N1/N2 timing evidence, the
  deployment runbook, and the shipped frontend freshness banner behavior.
- Document the chosen N3 evidence path in
  `docs/planning/phase_n3_monitoring_inventory.md`.
- Define the canonical smoke targets for N3 (`GET /`, `GET /health`,
  `GET /freshness`, and representative `/query` calls).
- Define which deployment headers/timing fields matter.
- List the custom-domain-specific checks that remain deferred to Phase N4.

**Files likely touched:**

- `docs/planning/phase_n3_monitoring_inventory.md` (new)
- Possibly `docs/planning/production_deployment_plan.md` if the workflow needs
  clarification

**Acceptance criteria:**

- Inventory names the current deployment-target rule.
- Inventory names the canonical smoke cases and evidence artifacts.
- Inventory identifies what N3 can finish without the custom domain.
- Inventory explicitly lists the remaining domain-gated work for N4.

**Tests to run:**

- None (reconnaissance only)

**Reference docs:**

- `docs/planning/phase_n1_e2e_results.md`
- `docs/planning/phase_n2_preview_ui_e2e_results.md`
- `docs/operations/deployment.md`
- `frontend/src/components/FreshnessStatus.tsx`

---

## 2. `[x]` Ship a reusable deployment smoke and monitoring harness - completed on 2026-05-02: `src/nbatools/deployment_monitoring.py` and `tools/deployment_smoke.py` now produce a machine-readable smoke report for any supplied base URL, `tests/test_deployment_monitoring.py` covers the monitoring logic, and `make test-preflight` passed.

**Why:** Monitoring and stability evidence should come from a repeatable tool,
not ad hoc terminal curls or browser sessions.

**Scope:**

- Add a reusable, domain-agnostic harness that accepts a base URL.
- Measure the canonical N3 endpoints and representative natural queries.
- Record status codes, timing, and selected deployment/runtime headers in a
  machine-readable report.
- Keep the tool usable against the current `*.vercel.app` deployment and a
  future custom domain without code changes.
- Update the deployment runbook with the monitoring command.

**Files likely touched:**

- `src/nbatools/deployment_monitoring.py` (new)
- `tools/deployment_smoke.py` (new)
- `docs/operations/deployment.md`
- `tests/test_deployment_monitoring.py` (new)

**Acceptance criteria:**

- A single command can run the smoke/monitoring pass against any supplied base
  URL.
- The report includes enough evidence for Phase N3 and the later custom-domain
  wrap-up.
- Failures are explicit and machine-readable.
- No hard-coded custom-domain assumptions remain in the harness.

**Tests to run:**

- `make test-preflight`

**Reference docs:**

- Item 1 inventory
- `docs/operations/deployment.md`

---

## 3. `[x]` Capture the first deployed monitoring baseline and freshness-banner evidence - completed on 2026-05-02: `phase_n3_preview_monitoring_baseline.md` records the first deployed smoke report, the freshness banner matched the live `/freshness` payload, and the watch-list routes were named for the soak.

**Why:** N3 should establish a real baseline before the 7-day soak starts.

**Scope:**

- Run the item 2 harness against the active deployed URL.
- Record the baseline in `docs/planning/phase_n3_preview_monitoring_baseline.md`.
- Verify the deployed UI freshness banner state against `/freshness` and note
  whether the banner matches the backend signal.
- Document any route whose first observed time should be watched during the
  soak.
- Flag any custom-domain-only verification still deferred to Phase N4.

**Files likely touched:**

- `docs/planning/phase_n3_preview_monitoring_baseline.md` (new)
- Possibly `docs/operations/deployment.md`

**Acceptance criteria:**

- Baseline captures status/timing/header evidence from the deployed URL.
- Freshness banner evidence matches the `/freshness` payload or documents a
  concrete mismatch.
- Watch-list routes are named for the soak.
- Deferred custom-domain checks are listed explicitly, not implied.

**Tests to run:**

- Run the item 2 harness against the active deployed URL
- Manual deployed-browser verification of the freshness banner

**Reference docs:**

- Item 1 inventory
- `docs/planning/phase_n2_preview_ui_e2e_results.md`

---

## 4. `[-]` Skip the 7-day deployed stability soak - skipped on 2026-05-02: friends-tier scope makes an extended synthetic soak lower value than ongoing real usage, while `phase_n3_stability_soak_log.md` preserves the day-0 baseline and the existing smoke harness remains available for targeted checks when needed.

**Why:** Friends-tier release scope does not justify holding Track B open for a
seven-day synthetic soak when the deployed app will now get real usage and the
day-0 baseline plus reusable smoke harness already provide a repeatable
fallback check.

**Scope:**

- Create `docs/planning/phase_n3_stability_soak_log.md` with day-0 evidence,
  check cadence, incident template, and current watch-list routes.
- Record the first soak entry using the item 2 harness and the active deployed
  URL.
- Define what counts as manual intervention, incident, and soak reset.
- Keep custom-domain-specific checks deferred to Phase N4 unless the domain is
  purchased during the soak.

**Files likely touched:**

- `docs/planning/phase_n3_stability_soak_log.md` (new)

**Acceptance criteria:**

- Soak log exists with the day-0 entry and an explicit skip/closure note.
- The queue item is marked `[-]` with the rationale captured inline.
- The retained baseline and smoke harness are named as the fallback evidence
  path.

**Tests to run:**

- Run the item 2 harness for the day-0 soak entry

**Reference docs:**

- Item 3 baseline
- `docs/operations/deployment.md`

---

## 5. `[x]` Phase N3 retrospective and Phase N4 handoff - completed on 2026-05-02: N3 shipped the reusable deployment smoke harness, captured deployed freshness/banner evidence against the live `*.vercel.app` URL, skipped the synthetic seven-day soak for friends-tier scope, and drafted `phase_n4_work_queue.md` so the remaining custom-domain closure work lives in one place.

**Why:** Self-propagating final task. Captures what N3 learned and drafts the
Track B wrap-up queue that closes the remaining custom-domain work.

**Scope:**

- Review the N3 monitoring, freshness, and soak results.
- Document what stabilized cleanly, what remained noisy, and what still
  depends on domain purchase.
- Draft `phase_n4_work_queue.md` with the exact remaining custom-domain,
  production-cutover, production-smoke, and Track B closure items.
- Update `production_deployment_plan.md` and
  `product_polish_master_plan.md` if the wrap-up path changed.

**Files likely touched:**

- `docs/planning/phase_n3_work_queue.md`
- `docs/planning/phase_n4_work_queue.md` (new)
- `docs/planning/production_deployment_plan.md`
- `docs/planning/product_polish_master_plan.md`

**Acceptance criteria:**

- Retrospective captures outcomes, surprises, and residual risks.
- `phase_n4_work_queue.md` exists with concrete wrap-up items.
- The remaining domain-gated work is explicit.
- This item is checked off only after the N3 monitoring/freshness work is
  closed, including an explicit decision on the soak path.

**Tests to run:**

- None (docs only)

**Retrospective:**

- What went well: the live `*.vercel.app` deployment was enough to build a
  reusable smoke harness, capture a baseline, and verify that the UI freshness
  banner matched the backend signal without waiting on the custom domain.
- What was harder: the seven-day synthetic soak would have held Track B open
  longer than warranted for a friends-tier app, while the domain gate still
  prevented the real production URL, cutover, and post-cutover smoke from
  happening.
- Residuals: Phase N4 now owns the remaining custom-domain setup, production
  cutover, production smoke, and final Track B closure work. The retained N3
  baseline and smoke harness stay available as comparison artifacts.

---

## Appendix: progress tracking

Phase N3 is now closed. Items 1-3 are checked `[x]`, item 4 is deliberately
skipped `[-]` for friends-tier scope, and item 5 has handed the remaining
custom-domain/cutover closure work to `phase_n4_work_queue.md`.
