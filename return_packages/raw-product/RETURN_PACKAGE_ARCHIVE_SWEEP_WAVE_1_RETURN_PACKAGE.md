# Return Package Archive Sweep Wave 1 Return Package

## Status

- Mode: execution.
- Execution date: 2026-05-23.
- Source directory: `return_packages/raw-product/`
- Destination directory:
  `return_packages/archive/raw-product/2026-05-raw-product-release-cycle/`
- Files deleted: none.
- Production code changed: no.
- Tests changed: no.
- QA corpus files changed: no.
- Generated outputs moved: no.
- Release statuses changed: no.
- Root `archive/` directory introduced: no.

## What Changed

Wave 1 executed the safe first archive sweep from
`docs/planning/raw-product/RETURN_PACKAGE_ARCHIVE_SWEEP_PREFLIGHT.md`.

The move set was generated as:

```text
all return_packages/raw-product/*.md
minus exact package paths linked from docs/, README.md, and AGENTS.md
```

Only doc-unlinked candidates were moved, using `git mv`, into:

```text
return_packages/archive/raw-product/2026-05-raw-product-release-cycle/
```

An archive manifest was added at:

```text
return_packages/archive/raw-product/2026-05-raw-product-release-cycle/ARCHIVE_MANIFEST.md
```

## Counts

| Count | Value |
| --- | ---: |
| Raw-product package files before move | 118 |
| Exact linked package paths from docs/README/AGENTS | 39 |
| Package files moved | 79 |
| Package files left active immediately after move | 39 |
| Package files left active after adding this Wave 1 return package | 40 |

## Move Policy

- Preserve every return package linked by `docs/`, `README.md`, or
  `AGENTS.md`.
- Move only unlinked package files from the flat raw-product package directory.
- Use `git mv` so Git records the archive operation as renames.
- Do not delete package evidence.
- Do not update release/readiness docs in Wave 1 because no linked package
  paths moved.

## Linked-Package Preservation Proof

Pre-move inventory:

- `return_packages/raw-product/*.md`: 118 files.
- Linked package paths from `docs/`, `README.md`, and `AGENTS.md`: 39.
- Archive candidates after subtracting the linked set: 79.
- Overlap between linked-package set and archive-candidate set: none.
- Missing linked paths before move: none.

Post-move validation:

- `return_packages/raw-product/*.md`: 39 files before this return package was
  added.
- Archived package files: 79.
- Every exact `return_packages/raw-product/..._RETURN_PACKAGE.md` path
  referenced from `docs/`, `README.md`, or `AGENTS.md` still exists.

## Files Changed Summary

| Area | Change |
| --- | --- |
| `return_packages/raw-product/` | Moved 79 doc-unlinked completed packages out of the active raw-product package directory. |
| `return_packages/archive/raw-product/2026-05-raw-product-release-cycle/` | Added the archived package files and `ARCHIVE_MANIFEST.md`. |
| `return_packages/raw-product/RETURN_PACKAGE_ARCHIVE_SWEEP_WAVE_1_RETURN_PACKAGE.md` | Added this execution return package. |

No production code, tests, QA corpus files, generated outputs, durable
release/readiness docs, or release statuses changed.

## Docs Reference Validation Result

Command shape:

```text
rg --no-filename -o "return_packages/raw-product/[A-Z0-9_]+_RETURN_PACKAGE\.md" docs README.md AGENTS.md | sort -u |
  while IFS= read -r path; do test -f "$path" || printf '%s\n' "$path"; done
```

Result: no missing paths were printed. Current docs links still resolve because
Wave 1 avoided linked packages entirely.

## Release Impact

No product or release impact. This is an evidence-organization sweep only.

The current Raw Product release/readiness docs still point to active package
paths, and those paths were preserved. The archive manifest now gives a stable
entry point for historical doc-unlinked package evidence from the May 2026 Raw
Product release cycle.

## Validation

| Command / check | Result |
| --- | --- |
| Docs/README/AGENTS exact package-reference scan | Passed; every referenced `return_packages/raw-product/..._RETURN_PACKAGE.md` path exists |
| `git diff --check` | Passed |
| `git diff --cached --check` | Passed |
| New-file whitespace checks | Passed for `ARCHIVE_MANIFEST.md` and this return package |
| Markdown lint availability | Not run; no `markdownlint`, `markdownlint-cli2`, `mdl`, or `mdformat` command was found on PATH |
