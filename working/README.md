# Working Files

`working/` is the tracked home for active task artifacts. Give each active task
one folder:

```text
working/<task-slug>/
```

Keep task-scoped plans, preflights, probes, triage notes, handoff notes, smoke
notes, screenshot notes, and return packages inside that folder. Return
packages belong to the relevant task folder; do not create a new standalone
return-package folder.

Before completing a task, promote durable facts into `docs/` as needed. Do not
put new working artifacts under `docs/`.

When the task is complete, move its folder to the separate top-level
`archive/<task-slug>/` location. `archive/` is ignored and is not inside
`working/`.

`outputs/` is fully gitignored and is for generated artifacts and evidence only.
Working files may cite generated output paths as task evidence, but durable
facts must be promoted into `docs/` before the task is closed. Tests and corpora
must use tracked fixtures outside `outputs/` when they need stable input data.
