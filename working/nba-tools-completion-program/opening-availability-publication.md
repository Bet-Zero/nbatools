# Verified opening-game availability publication

The acquired 2025-10-21 Warriors–Lakers overlay contains 34 source-listed players:
20 played and 14 explicitly did not play. It does not certify other games,
season-wide absence coverage, injury inference, or completed query support.

Required source run [39002683645](https://github.com/Bet-Zero/nbatools/actions/runs/39002683645)
executed/passed its sole required test without skips on reviewed code
`631b259a10be675be9a97da93ebc38053a274e79` and base
`queue-d-production-0574735-20260716`. Artifact `12090016663` ZIP SHA256:
`35e7b0294dd64b7c8752351dd05d45129ea8977d16bd3cad0140033b447f53dd`.
Independent checker `/root/availability_checker` verified every played name/minute,
all nonparticipation reasons, source receipts, profile linkage and import digest.

The inventory beside this document lists the exact eight generation-relative R2
object paths, byte sizes and SHA256 values. The overlay adds 375400 bytes before
full immutable-generation packaging. No raw fixture data is included. Preserve
all source files; the official profile proves identity only, while the dated
scorer report establishes membership and participation.

## Existing operator process

Use the project's existing authorized publication environment and reviewed PR468
code. Runtime and `r2-validation` credentials remain read-only. The script does
not request, create, print, or reconfigure credentials. No permanent R2 write has
been performed by this handoff.

Obtain the artifact with existing GitHub access and extract it. Its `acquired_data`
directory must contain exactly the files in the inventory. In an environment
with the reviewed project installed, offline verification is:

```bash
python working/nba-tools-completion-program/publish-opening-availability.py \
  --artifact-dir /path/to/extracted/acquired_data
```

For actual authorized publication, run the same verified script with the existing
operator-controlled write authority supplied to that command process:

```bash
python working/nba-tools-completion-program/publish-opening-availability.py \
  --artifact-dir /path/to/extracted/acquired_data \
  --work-dir work/availability-publication-20261017 \
  --code-root /path/to/reviewed/nbatools \
  --publish
```

The script binds imports to `--code-root` (default: its repository), verifies the
reviewed pipeline/data-source file hashes, and rejects a wrong editable install
before any R2 access. The work directory must not already exist. `--prepare` can replace `--publish`
for full local validation without remote writes; use a new work directory for
any subsequent invocation. The script downloads/verifies the full active
snapshot, refuses a changed base or conflicting existing overlay, preserves core
data and freshness metadata, runs the existing full local generation validator,
and calls the existing immutable publisher with `expected_base` protection.
It never prunes generations or changes cost/permission settings.

Retain `base-manifest.json`, `local-validation.json` and `publication.json` from
the work directory. The existing publisher verifies every uploaded object's size
and SHA256 metadata before conditionally switching the active pointer. After
publication, separately verify the new active generation through read-only R2
access and deployed readiness/representative queries; publication alone does not
close runtime or query-feature acceptance. If the base changed, investigate and
revalidate rather than changing the expected base value to force publication.
