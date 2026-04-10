# AGENTS.md

This file tells coding agents how to work in the `nbatools` repo.

## Project goal

`nbatools` is being built toward a **UI-based NBA search app with text input**.

The current CLI is the development interface and a power-user surface. It is **not** the final product. Work in this repo should strengthen the reusable search and analytics engine that a future UI and API can call.

That means:

- core logic should remain **UI-agnostic**
- natural query behavior should remain **transport-agnostic**
- CLI wrappers should stay thin
- machine-readable outputs should stay stable enough for future UI/API reuse

## Working style

Agents working in this repo should:

- prefer small, targeted changes over broad rewrites
- preserve existing public behavior unless the task explicitly changes it
- keep parser logic, command logic, data processing, and formatting separated
- avoid editing unrelated files while implementing a feature
- tighten duplication when touching an area that already shows repeated logic
- leave the repo in a cleaner state than they found it when reasonable

Do not introduce architecture churn without a concrete reason tied to maintainability, correctness, or long-term UI/API readiness.

## What this repo is optimizing for

The current phase is about building a durable NBA search engine, not just a CLI.

Priority order:

1. correct data behavior
2. stable command/query semantics
3. test coverage
4. reusable output contracts
5. CLI presentation
6. future UI readiness

## Change rules

### General rule

When adding or changing a feature, agents should usually follow this order:

1. implement or extend the underlying structured behavior
2. wire or update natural query routing
3. add or update tests
4. update docs for verified shipped behavior

A feature should not be treated as shipped if docs changed but tests or behavior did not.

### Command-layer rule

Do not put business logic directly in CLI entrypoints or Typer command wrappers.

- `src/nbatools/cli.py` and `src/nbatools/cli_apps/*` are for command registration, argument handling, and export plumbing
- real query or analytics logic belongs in `src/nbatools/commands/*`

### Natural query rule

`src/nbatools/commands/natural_query.py` is a routing/orchestration layer.

It may contain:

- intent detection
- alias resolution
- route selection
- natural language parsing helpers
- orchestration across structured commands

It should **not** become an unmanaged dumping ground for unrelated business logic.

If a feature requires substantial new computation, reusable filtering logic, or domain-specific analysis, move that logic into a dedicated command/helper module.

### Duplication rule

When touching duplicated route branches, duplicate post-processing, or repeated helper logic, agents should prefer cleanup instead of adding a third copy.

Do not knowingly leave behind:

- dead branches
- duplicate route handling
- one-off compatibility hacks with no comment or cleanup plan
- silent behavior forks between player/team paths unless justified

## Testing expectations

Every meaningful feature change should include appropriate tests.

### Minimum expectations by change type

- parsing change -> parser tests
- output behavior change -> smoke tests
- new calculation or metric -> formula/unit tests
- export behavior change -> export tests
- regression fix -> regression test covering the bug

### Required mindset

- do not claim a feature is supported just because one manual example worked
- do not update README or current-state docs unless the behavior is verified
- do not remove tests to make a failing implementation look clean

## Documentation expectations

Each doc has a specific role.

- `README.md` -> user-facing overview and high-level examples
- `docs/current_state_guide.md` -> verified shipped behavior only
- `docs/roadmap.md` -> planned or next capabilities
- `docs/project_conventions.md` -> architecture and engineering rules
- `docs/data_contracts.md` -> dataset definitions and expectations

Agents should keep these boundaries clean.

In particular:

- do not put roadmap material into current-state docs
- do not advertise unsupported or untested behavior in README
- do not silently broaden claims without code and tests backing them up

## Output and interface expectations

Outputs in this repo serve multiple consumers:

- CLI pretty output
- raw/export output
- future UI/API layers

Agents should treat raw command output as part of the engine contract.

Guidelines:

- pretty formatting is presentation only
- structured/raw outputs should remain machine-readable
- future UI should be able to reuse the same underlying command/query results
- avoid coupling core logic to terminal-only assumptions

## Assumptions agents must not make

Agents must **not** assume:

- the CLI is the final product
- current docs are automatically correct
- one passing example means broad support
- all logic belongs in `natural_query.py`
- all data will remain CSV forever
- a refactor is justified just because it feels cleaner

CSV + pandas is the current local-first implementation model. That is acceptable for now. Any storage-layer change should be justified by a real need, not novelty.

## Preferred implementation mindset

When in doubt, optimize for:

- explicitness over cleverness
- correctness over breadth
- reusable internals over CLI-only shortcuts
- stable contracts over ad hoc output tweaks
- documented and tested behavior over implied behavior

## If adding a new feature

Use this checklist:

- Does the behavior belong in an existing command, or does it need a new one?
- Is the new behavior expressible in structured form?
- Does natural query routing map cleanly to that structured behavior?
- Are parser tests updated if parsing changed?
- Are smoke tests added if output/behavior changed?
- Are docs updated only after verification?
- Does this move the repo toward a reusable UI-ready engine?

If the answer to the last question is no, rethink the implementation.
