# AGENTS.md

Rules for coding agents in `Bet-Zero/nbatools` (NBA Tools, not ScoutZero).
This file holds only current rules. Older dated layers were removed on 2026-11-12;
their full text is in Git history (`git show 95cb705:AGENTS.md`). Nothing below
weakens a safeguard that existed before.

## Start of a session

1. Read this file, then the **Resume checkpoint** in
   `working/nba-tools-completion-program/README.md`. Read `ROADMAP.md` only when
   choosing between milestones.
2. Check live `main`, open PRs and any branch you are resuming. Preserve newer
   work; never reset or force-push another session's branch.
3. Do the checkpoint's next action. Read only the code, docs and PRs it needs.
   Do not restart a whole-project audit or ask the owner for test questions.

## The product

NBA Tools is a web NBA statistics search app. A person types an ordinary question
and gets the correct answer, with the subject, conditions, sample and metric
they asked for. One Python engine serves the web app (React), API and CLI.
Computation, filters and interpretation live in the engine; UI and CLI stay thin.
Data scope is the 1996-97 season onward.

## Correctness rules (never relax these)

- **A refusal is not a feature.** A desired question is unfinished until it gets
  the correct answer. Never turn a legitimate positive test into a refusal,
  skip or xfail to get green.
- **Missing is not zero.** Never invent a value, fill an unknown with zero, or
  mark provisional data as accepted.
- **Participation is not injury, status or on-court presence.** A missing game
  row does not prove a player was injured or out; a played row does not prove
  healthy or available. Never infer team nonmembership or a DNP from missing
  rows, a roster snapshot or another game on the same date. Do not encode
  `available = played` in code or tests.
- **Meaning before numbers.** Check that the answer kept the subject, team,
  season, conditions and grain before checking values. Expected NBA values come
  from qualified source rows or controlled fixtures, never from the app's own
  calculation. Two engine paths agreeing is not an independent check.
- **Fix shared logic, not phrases.** Repair the shared interpretation or
  calculation; don't add per-question special cases. A third patch for the
  same root cause means the shared representation needs fixing.
- **No rewrite.** Keep the engine, calculations, result contracts, React app,
  immutable data generations and useful tests. Splitting files is not progress.

## Who decides what

Agents own implementation, prioritization, data research, numerical checking,
review coordination, merging and handoffs. The owner (B) does not review or
merge PRs.

Ask B only for: a real product-meaning choice, production data publication or
an R2 active-pointer change, new costs, credentials or permissions, substantial
bulk backfills, destructive operations, or weakening a safeguard. Bring one
recommendation and the smallest exact action. Never fake an approval.

Standing limits until B changes them:

- Routine, bounded collection of public NBA data through the existing approved
  routes is allowed (owner, 2026-11-01). Automatic or unattended refresh is not.
- Runtime and validation credentials stay read-only. Publication stays behind the
  existing protected approval. Fixed-plan limits and $0 metered overage stay.
- Don't change Vercel settings, secrets, deployment protection, branch
  protection or R2 publication gates. Public query-feedback persistence stays
  disabled. No new paid service, model access or hosting migration.
- Launch and branding are B's decisions.
- Agent 2 (data-quality worker) is stopped. DQ-005 and K12 cold-start chasing are
  parked. The exhausted 484-rate investigations stay closed without new evidence.

## How work runs

- **One lead** owns integration and the checkpoint. **One writer** owns the
  shared parser/request/service code at a time. At most one other truly
  independent lane, plus a separate checker. Don't invent parallel capacity, and
  never claim background work that isn't actually running.
- One PR per logical unit. Reproduce the defect, fix it, run focused tests,
  get review where required, pass the gates, merge.
- Before starting optional work, write one line in the PR saying which Core-1
  requirement or confirmed defect it serves. Other discoveries go in the
  checkpoint's carry-forward list, not a new tracker or ticket.
- If a requirement is blocked by missing source data, record the exact missing
  evidence once and move to independent work. Don't rerun the same failing
  checks or pile unrelated work onto a red branch.

## Checking: match it to the risk

| Change | Required before merge |
| --- | --- |
| Docs, checkpoint, evidence notes (Markdown only) | `make docs-governance`, `git diff --check`, accurate self-review. CI takes its light path. |
| Data correction with retained source proof | New immutable data version (originals and prior versions kept), tests for the affected consumers, targeted real-data (R2) run, independent review. |
| Parser, calculation, query or verification-gate change | Focused tests while editing, blocking CI, targeted real-data run for affected cases, independent review with unfamiliar wording and independently derived expectations. |
| Frontend change | Locked install, build, lint, tests; look at the changed rendering. |
| Release candidate | Freeze it. Then once: full Raw QA replay, filter sweep, full test suite and desktop/mobile deployed checks. |

Broad replays and deployed desktop/mobile captures run **once per release
candidate**, not per PR. Each PR still checks the behavior it changed.

**Independent review** means a separate agent session, not self-review. Record
the reviewer, the reviewed revision and any open findings in the PR. Green CI
alone is not review. A bot comment is not review.

**Reuse passing evidence** when the code, data and conditions it covered are
unchanged. Say which revision it came from. Don't rerun a passing check without
a reason to expect a different result.

**Before writing new verification code,** check it against the real source
schema, an actual native API response, the existing test contract and a known
good sample. Most past verifier rework came from skipping this.

## CI, validation and data safeguards

- Keep the `.github/workflows/ci.yml` checks: lint, docs-governance,
  frontend-verify, blocking production frontend-security, informational
  frontend-security-dev, test-fast on application PRs and test-full on
  application main pushes and nightly. Never suppress failures, remove
  backstops, raise thresholds or weaken assertions. `CONTRIBUTING.md` has the
  exact selection rules.
- A required numerical check counts only if it actually ran and passed. Empty
  selections, all-skipped runs, informational failures or a green outer
  workflow are not acceptance.
- Real-data validation uses the existing R2 workflow and its `r2-validation`
  environment. After independent review, agents may start a targeted run by
  pushing a manifest-only request commit to a fresh `r2-validation/**` branch,
  as described in `docs/operations/deployment.md`. Ordinary CI stays secret-free.
- Keep raw, processed and derived layers and each dataset's grain. New data
  needs source, row meaning, keys, coverage rules and missing-data behavior in
  `docs/reference/data_contracts.md`. Before data work, follow
  `docs/operations/data_availability.md` and reuse qualified retained data.
  Corrections create new immutable versions; never mutate data a test is using.
  Fixtures are never published as real data. Never relabel old data as fresh.
- Useful commands: `make test-parser`, `test-query`, `test-engine`, `test-api`,
  `test-output` while editing; `make test-preflight` or `make test` for high
  fan-in changes; `make raw-query-answer-qa` is a failing gate.

## Handoffs and documentation

- The Resume checkpoint is the only active queue. **Replace** it with current
  state in plain English; keep it to about one screen. PR-specific detail stays
  in the PR. Update it before a merge that changes the next action, a block or a
  session stop: branch and SHA, data version, what passed, open findings, the
  one next action.
- Durable docs go in `docs/reference/` (behavior), `docs/architecture/`,
  `docs/operations/` (runbooks), `docs/audits/` (history), per
  `docs/operations/working_and_archive_policy.md`. Task material goes in
  `working/`. Don't create another status system.
- Raw QA human-review fields keep their literal meaning. Never invent
  `human_review_complete` or a named human reviewer.
- Owner updates lead with **Now answers; Still unfinished; Verification; Next;
  Needed from you (normally nothing)**, in plain basketball terms. Don't narrate
  routine checks.

When Graphify is available, use scoped navigation and refresh it after code
changes. It is never a prerequisite for delivery work.
