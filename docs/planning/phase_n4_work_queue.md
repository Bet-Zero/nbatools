# Phase N4 Work Queue

> **Role:** Sequenced, PR-sized work items for Phase N4 of
> [`production_deployment_plan.md`](./production_deployment_plan.md) -
> _Custom-domain closure, production cutover, production smoke, and Track B
> wrap-up._
>
> **Current gate:** As of 2026-05-02, the production domain has not been
> purchased or chosen yet. The deployed `*.vercel.app` URL remains the live
> friends-tier surface until the custom domain exists.
>
> **How to work this file:** Find the first unchecked item below. Review the
> reference docs it cites. Execute per its acceptance criteria. Run the test
> commands. Check the item off, commit, open a PR, wait for CI, merge when
> green, then continue to the next unchecked item. If an item is blocked on the
> missing custom domain, mark it `[~]` with the exact developer action required
> and continue to any later domain-independent item. Stop only when no remaining
> item can make progress without the developer.

---

## Status legend

- `[ ]` - not started
- `[~]` - in progress or blocked on a named external step
- `[x]` - complete and merged
- `[-]` - skipped (with inline note explaining why)

---

## 1. `[ ]` Re-complete N2 item 4: custom domain and HTTPS

**Why:** Track B is not closed until friends use a real custom-domain URL with
clean HTTPS.

**Scope:**

- Choose or purchase the final production domain.
- Add the domain in the Vercel project.
- Configure the DNS records Vercel requires.
- Wait for DNS propagation and HTTPS certificate issuance.
- Document the final domain, DNS record values, and verification result.

**Files likely touched:**

- `docs/operations/deployment.md`
- `docs/planning/phase_n4_domain_cutover_results.md` (new, if useful)

**Acceptance criteria:**

- The custom domain resolves to the Vercel deployment.
- HTTPS is active without browser warnings.
- Root UI and API endpoints work over the custom domain.
- Required manual domain/DNS steps are documented for future operators.

**Tests to run:**

- Manual browser check against the custom domain
- Manual `GET /health` and `GET /freshness` against the custom domain

**Reference docs:**

- `docs/planning/phase_n2_work_queue.md`
- `docs/operations/deployment.md`

---

## 2. `[ ]` Draft the custom-domain cutover worksheet and operator checklist

**Why:** Once the domain exists, the cutover and smoke steps should execute
from a concrete checklist instead of reconstructing the operator procedure.

**Scope:**

- Create `docs/planning/phase_n4_domain_cutover_checklist.md`.
- Capture the exact operator sequence for domain purchase/selection,
  Vercel-domain attachment, DNS verification, production readiness checks,
  deploy-on-main evidence capture, and post-cutover smoke commands.
- Name the evidence artifacts that items 3-4 will populate.
- Make the checklist reusable whether the final domain uses apex-only or apex
  plus `www` hostnames.

**Files likely touched:**

- `docs/planning/phase_n4_domain_cutover_checklist.md` (new)
- `docs/operations/deployment.md`
- `docs/index.md`

**Acceptance criteria:**

- The checklist gives the operator an exact cutover order.
- DNS and Vercel steps are explicit rather than implied.
- The smoke/evidence commands for later N4 items are named.
- The checklist does not assume the custom domain already exists.

**Tests to run:**

- None (docs only)

**Reference docs:**

- `docs/planning/phase_n2_work_queue.md`
- `docs/planning/phase_n3_preview_monitoring_baseline.md`
- `docs/operations/deployment.md`

---

## 3. `[ ]` Re-complete N2 item 5: production cutover and deploy-on-main evidence

**Why:** The app is not really in production until the custom-domain deployment
path, R2-backed production configuration, and deploy-on-main evidence are
documented.

**Scope:**

- Execute the checklist from item 2 after the custom domain is live.
- Confirm Vercel production environment variables still point at R2.
- Confirm the latest synced data is available before cutover.
- Document which merge/deployment serves as the production deploy-on-main
  evidence record.

**Files likely touched:**

- `docs/planning/phase_n4_domain_cutover_results.md` (new)
- `docs/operations/deployment.md`

**Acceptance criteria:**

- Production reads from R2.
- The custom domain serves the real UI from the intended production deployment.
- `/health`, `/freshness`, `/query`, and `/structured-query` work on the
  custom domain or any blocker is documented clearly.
- The deploy-on-main evidence path is recorded for item 4.

**Tests to run:**

- Manual production readiness smoke against the custom domain

**Reference docs:**

- `docs/planning/phase_n4_domain_cutover_checklist.md`
- `docs/planning/phase_n1_e2e_results.md`
- `docs/operations/deployment.md`

---

## 4. `[ ]` Re-complete N2 item 6: custom-domain production smoke and performance record

**Why:** After cutover, Track B still needs a recorded production baseline and
proof that the real domain works end to end.

**Scope:**

- Run the deployment smoke harness against the custom domain.
- Verify UI workflows against the custom domain in the browser.
- Record cold/warm timings and any watch-list routes.
- Confirm the deploy-on-main evidence captured in item 3 matches the observed
  production deployment.

**Files likely touched:**

- `docs/planning/phase_n4_production_smoke_results.md` (new)

**Acceptance criteria:**

- Production UI and API smoke passes on the custom domain.
- Deploy-on-main evidence is documented with commit/deployment status.
- Cold/warm timings are recorded.
- Any route above the watch threshold is flagged for follow-up.

**Tests to run:**

- `./.venv/bin/python tools/deployment_smoke.py --base-url https://<custom-domain>`
- Manual production browser verification against the custom domain

**Reference docs:**

- `docs/planning/phase_n4_domain_cutover_checklist.md`
- `docs/planning/phase_n3_preview_monitoring_baseline.md`

---

## 5. `[ ]` Track B closure retrospective and master-plan handoff

**Why:** Self-propagating final task. Closes Track B cleanly and records the
final deployment state instead of leaving the remaining domain work implicit.

**Scope:**

- Review N1-N4 outcomes, surprises, and residual risks.
- Confirm Track B's done definition is fully met.
- Update `production_deployment_plan.md` and
  `product_polish_master_plan.md` with Track B closure status.
- Update any planning/index docs that should no longer describe Track B as
  active.

**Files likely touched:**

- `docs/planning/phase_n4_work_queue.md`
- `docs/planning/production_deployment_plan.md`
- `docs/planning/product_polish_master_plan.md`
- `docs/index.md`

**Acceptance criteria:**

- Retrospective captures what worked, what was noisy, and final residuals.
- Track B's done definition is verified against shipped evidence.
- The master plan no longer treats Track B as an open continuation.
- This item is checked off only after items 1-4 are complete.

**Tests to run:**

- None (docs only)

---

## Appendix: progress tracking

Phase N4 is complete when items 1-5 are checked `[x]`. Item 2 can complete
before the custom domain exists. Items 1, 3, and 4 require the domain, and item
5 closes the track after those production proofs exist.
