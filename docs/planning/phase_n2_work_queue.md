# Phase N2 Work Queue

> **Role:** Sequenced, PR-sized work items for Phase N2 of
> [`production_deployment_plan.md`](./production_deployment_plan.md) -
> _Frontend deployment, custom domain, and production cutover._
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

## 1. `[x]` Audit the frontend deployment path and choose the build strategy — completed: `phase_n2_frontend_deployment_inventory.md` chooses a Vercel build-time Vite build, keeps generated `dist/` assets out of git, and defines the item 2 punchlist for build command, asset serving, tests, docs, and preview verification.

**Why:** Phase N1 intentionally shipped the API fallback because the React
bundle was not part of the Vercel deployment. Before changing build behavior,
document whether N2 should commit built assets, run the Vite build during
Vercel deployment, or use another repo-native approach.

**Scope:**

- Inspect the current Vite output path (`src/nbatools/ui/dist/`), package data
  inclusion, `.gitignore`, `vercel.json`, Vercel build behavior, and CI
  frontend scripts.
- Document the chosen build strategy and tradeoffs in
  `docs/planning/phase_n2_frontend_deployment_inventory.md`.
- Identify any Vercel constraints that could affect Python Functions plus Node
  frontend build in one deployment.
- Confirm the strategy keeps the React frontend a thin presentation layer and
  preserves same-origin API calls.

**Files likely touched:**

- `docs/planning/phase_n2_frontend_deployment_inventory.md` (new)
- Possibly `docs/planning/production_deployment_plan.md` if the strategy
  changes Phase N2 scope

**Acceptance criteria:**

- Inventory states the selected frontend build/deploy strategy.
- Inventory names exact files/settings that item 2 should change.
- Residual risks and rollback/fallback path are documented.
- No unsupported behavior is advertised as shipped.

**Tests to run:**

- None (reconnaissance only)

**Reference docs:**

- `docs/operations/ui_guide.md`
- `vercel.json`
- `frontend/vite.config.ts`
- `frontend/package.json`
- `src/nbatools/api_ui.py`

---

## 2. `[ ]` Ship the React bundle in the Vercel preview

**Why:** The deployed API works, but `/` still serves the fallback shell. N2's
first functional milestone is a preview URL where the real React app loads and
talks to the same deployed API functions.

**Scope:**

- Implement the build/deploy strategy chosen in item 1.
- Ensure `GET /` returns the built React UI instead of the fallback when the
  bundle exists.
- Ensure built assets are available from the deployed Vercel preview.
- Keep API routes (`/health`, `/freshness`, `/routes`, `/query`,
  `/structured-query`) unchanged.
- Update operations docs with the production-like frontend build workflow.

**Files likely touched:**

- `vercel.json`
- `frontend/`
- `src/nbatools/ui/dist/` or build configuration, depending on item 1
- `docs/operations/ui_guide.md`
- `docs/operations/deployment.md`

**Acceptance criteria:**

- `GET /` on the preview renders the React app, not the fallback.
- Frontend assets load with HTTP `200`.
- Same-origin API calls from the UI work against deployed functions.
- The fallback remains available for checkouts without a built bundle.
- Local production-like workflow still works.

**Tests to run:**

- `cd frontend && npm run build`
- `cd frontend && npm run test`
- `make test-api`
- Manual: preview `/`, `/health`, `/freshness`, and one `/query` call

**Reference docs:**

- Item 1 inventory
- `docs/operations/ui_guide.md`
- AGENTS.md "Frontend-layer rule"

---

## 3. `[ ]` Verify preview UI workflows end-to-end

**Why:** Loading the UI is not enough; the deployed React app must execute the
core user workflows against R2-backed API functions.

**Scope:**

- Use the preview URL from item 2.
- Verify first-run load, health indicator, freshness display, natural query
  execution, result rendering, raw JSON toggle, copy link, saved-query basics,
  and query history.
- Exercise the same representative queries from N1:
  - `Jokic last 10`
  - `top 10 scorers 2025-26`
  - `Jokic summary (over 25 points and over 10 rebounds) 2025-26`
- Verify at desktop and phone-sized viewport targets.
- Document results in `docs/planning/phase_n2_preview_ui_e2e_results.md`.

**Files likely touched:**

- `docs/planning/phase_n2_preview_ui_e2e_results.md` (new)
- Possibly frontend files if verification finds UI-only defects

**Acceptance criteria:**

- Preview UI completes the representative query workflows.
- Result renderers show the expected sections for summary and leaderboard
  responses.
- Mobile viewport smoke does not show broken layout, overlapping text, or page
  widening.
- Any defects found are fixed or documented as explicit blockers.

**Tests to run:**

- `cd frontend && npm run test`
- Manual browser/viewport verification against preview

**Reference docs:**

- `docs/operations/ui_guide.md`
- `docs/planning/phase_n1_e2e_results.md`

---

## 4. `[ ]` Configure the custom domain and HTTPS - human-gated

**Why:** Track B is not done until the product is reachable on a custom-domain
URL with clean HTTPS. This step requires the developer to own or purchase the
domain and make DNS changes.

**Scope:**

- Developer chooses or purchases the production domain.
- Add the domain to the Vercel project.
- Configure DNS records as directed by Vercel.
- Wait for DNS and certificate provisioning.
- Document exact domain, DNS record type/target, and verification status in
  `docs/operations/deployment.md`.

**Files likely touched:**

- `docs/operations/deployment.md`
- `docs/planning/phase_n2_domain_cutover_results.md` (new, if useful)

**Acceptance criteria:**

- Custom domain resolves to the Vercel deployment.
- HTTPS certificate is active and browser requests show no certificate warning.
- Root UI and API endpoints work over the custom domain.
- Required manual DNS/domain steps are documented for future operators.

**Tests to run:**

- Manual browser check against the custom domain
- Manual `GET /health` and `GET /freshness` against the custom domain

**Reference docs:**

- Vercel domain configuration docs
- `docs/operations/deployment.md`

**Human-gate rule:**

If the domain is not available or DNS cannot be changed by the agent, mark this
item `[~]` with the exact developer action needed and stop.

---

## 5. `[ ]` Prepare production cutover and deploy-on-main evidence path

**Why:** The preview can pass while production is still incomplete. This item
prepares the actual production deployment path so the next item can verify the
custom-domain production deployment created by this item's merge to `main`.

**Scope:**

- Confirm Vercel production environment variables include `DATA_SOURCE=r2` and
  the R2 variables from `docs/operations/deployment.md`.
- Ensure the latest synced R2 data is available before cutover.
- Verify the custom domain points to the production deployment.
- Document which merge/deployment should be used as the deploy-on-main evidence
  at the start of item 6.

**Files likely touched:**

- `docs/planning/phase_n2_domain_cutover_results.md` (new)
- Possibly `docs/operations/deployment.md`

**Acceptance criteria:**

- Production environment is configured to read from R2.
- Custom domain is ready to serve the real React UI from production.
- `/health`, `/freshness`, `/query`, and `/structured-query` work on the
  custom domain or any blocker is documented clearly.
- The item 5 PR merge is expected to trigger the production deployment that
  item 6 verifies.

**Tests to run:**

- Manual production readiness smoke against the custom domain

**Reference docs:**

- `docs/planning/phase_n1_e2e_results.md`
- `docs/operations/deployment.md`

---

## 6. `[ ]` Production UI/API smoke, deploy-on-main, and performance record

**Why:** After cutover, capture the production baseline and deploy-on-main
evidence that Phase N3's monitoring and stability soak can compare against.

**Scope:**

- Measure cold/warm timings on the custom domain for:
  - `GET /`
  - `GET /freshness`
  - `POST /query` with `Jokic last 10`
  - `POST /query` with `top 10 scorers 2025-26`
  - `POST /query` with the complex Jokic multi-filter query
- Verify UI workflows from item 3 against the custom domain.
- Confirm the item 5 merge to `main` triggered a Vercel production deployment.
- Confirm root, assets, and API calls return cache/runtime behavior that is
  acceptable for friends-tier use.
- Document the production baseline in
  `docs/planning/phase_n2_production_smoke_results.md`.

**Files likely touched:**

- `docs/planning/phase_n2_production_smoke_results.md` (new)

**Acceptance criteria:**

- Production UI and API smoke passes.
- Deploy-on-main evidence is documented with commit/deployment status.
- Cold/warm timings are recorded.
- Any route above 5s first-observed is flagged for Phase N3 monitoring or
  optimization follow-up.
- No auth failures, CORS failures, asset 404s, API timeouts, or result-parity
  mismatches.

**Tests to run:**

- Manual production e2e against custom domain

**Reference docs:**

- `docs/planning/phase_n2_preview_ui_e2e_results.md`
- `docs/planning/phase_n1_e2e_results.md`

---

## 7. `[ ]` Phase N2 retrospective and Phase N3 handoff

**Why:** Self-propagating final task. Captures deployment lessons and drafts
the next queue for monitoring, freshness, and stability.

**Scope:**

- Review every checked item above: outcomes, surprises, residuals.
- Document any deployment/domain/frontend-build issues that should be
  remembered.
- Draft `phase_n3_work_queue.md` with concrete items for monitoring,
  production freshness, alerting, and the 7-day stability soak.
- Update `production_deployment_plan.md` and `product_polish_master_plan.md`
  so the active continuation points to Phase N3.

**Files likely touched:**

- `docs/planning/phase_n2_work_queue.md` - check this item, add retrospective
- `docs/planning/phase_n3_work_queue.md` (new)
- `docs/planning/production_deployment_plan.md`
- `docs/planning/product_polish_master_plan.md`

**Acceptance criteria:**

- Retrospective captures what went well, what was harder, and residuals.
- `phase_n3_work_queue.md` exists with concrete PR-sized items.
- The final item of N3 drafts N4.
- This item is checked off.

**Tests to run:**

- None (docs only)

---

## Appendix: progress tracking

When all items above are checked `[x]`, Phase N2 is complete. The draft of
`phase_n3_work_queue.md` from item 7 is the handoff artifact.
