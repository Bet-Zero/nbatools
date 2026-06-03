# Working and Archive Policy

## Purpose

`docs/` is for durable source-of-truth documentation only. Active task artifacts
belong in a tracked top-level `working/` folder so temporary materials stay
task-scoped without competing with durable documentation.

When a task is complete, promote any durable facts into `docs/` as needed, then
move the task folder into the separate top-level ignored `archive/` folder.

## Folder Structure

```text
docs/                         # durable source-of-truth documentation only
working/                      # tracked active-task working artifacts
  <task-slug>/
archive/                      # ignored completed-task working artifacts
  <task-slug>/
outputs/                      # generated artifacts and evidence only
return_packages/              # legacy ignored migration protection only
```

`archive/` is a top-level folder. It must not be created inside `working/`.

## Tracked and Ignored Rules

- `working/` remains tracked. Do not add ignore rules for `working/` or
  `working/*`.
- `archive/` is gitignored because completed working artifacts are historical
  local material.
- Keep the existing top-level `return_packages/` ignore rule as legacy
  protection during migration. Do not create new standalone return-package
  folders or place new return packages there.
- Do not put new working artifacts under `docs/`.

## Task Lifecycle

1. Create one tracked task folder at `working/<task-slug>/`.
2. Keep temporary task artifacts, including any return package, inside that
   folder while the task is active.
3. Before closing the task, promote durable facts into the appropriate `docs/`
   document when needed.
4. Move the completed task folder to `archive/<task-slug>/`.

Archived working files are historical and local only. They are not
source-of-truth documentation.

## What Belongs in `working/<task-slug>/`

- plans and preflights for the active task
- task-scoped return packages
- probes and triage notes
- handoff notes and smoke notes
- screenshot notes
- other temporary work artifacts for that task

Return packages are task-scoped working documents. They are not durable docs and
not their own top-level folder. A return package belongs inside the relevant
`working/<task-slug>/` folder while the task is active.

## What Belongs in `docs/`

- current-state reference documentation
- architecture decisions and conventions
- operational runbooks and policies
- durable audit records

Durable facts from working artifacts must be promoted into `docs/` before the
task folder is archived.

## What Belongs in `archive/<task-slug>/`

- the completed task folder moved from `working/<task-slug>/`
- its historical return package
- its completed probes, temporary notes, and task-local handoff materials

The top-level `archive/` folder is separate from `working/`. Archived working
files are historical/local only and must not be treated as source of truth.

## Generated `outputs/` Artifacts

`outputs/` may contain generated reports, screenshots, JSONL reports, review
artifacts, and manifests. These files are generated evidence only. They are not
durable source-of-truth documentation. Promote any long-lived conclusion into
the appropriate durable doc.

`outputs/` remains fully gitignored. Do not track subsets of `outputs/`; if a
test or corpus needs fixture data, put the fixture under a tracked fixture path
outside `outputs/`.

Durable docs may reference `outputs/` only as generated evidence paths,
generated artifact destinations, export examples, or validation snapshots whose
durable conclusion is summarized in docs. Do not make an ignored generated file
the only source of a product fact, release decision, test input, or corpus
contract.

Timestamped run directories should be retained only while they are useful:

- keep the latest successful run per workflow
- keep active investigation runs
- keep exact paths cited by tracked working files while that work is active
- keep local evidence needed to reproduce a current validation snapshot
- keep test-required fixtures only when those fixtures live outside `outputs/`

Older generated runs should be deleted after the relevant task closes or the
durable fact has been promoted. Completed working notes belong in `archive/`;
bulk generated outputs do not need to be archived by default.
