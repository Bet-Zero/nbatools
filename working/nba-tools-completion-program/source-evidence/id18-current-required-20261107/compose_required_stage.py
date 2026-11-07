"""Compose reviewed existing source stages into a new explicit development version."""

import io
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from nbatools.commands.pipeline.reported_absence_reasons import validate_publication
from nbatools.commands.validation_control import build_slice_manifest
from nbatools.development_data import MANIFEST, DevelopmentSnapshot, sha256
from tools.development_snapshot import _safe_contracts, intake_report, write_json

E = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
SOURCE = E / "current-required"
VERSION = "current123-required-source-development-v3"


def compose(output: Path, backlog: Path):
    if output.exists():
        raise ValueError("Use a new immutable output destination")
    binding = json.loads((E / "binding.json").read_bytes())
    raw = (E / binding["archive"]).read_bytes()
    assert sha256(raw) == binding["archive_sha256"]
    with ZipFile(io.BytesIO(raw)) as z:
        z.extractall(output)
    parent_sha = sha256((output / MANIFEST).read_bytes())
    assert parent_sha == binding["manifest_sha256"]
    DevelopmentSnapshot(output, parent_sha)
    artifacts = json.loads((SOURCE / "artifacts.json").read_bytes())
    source_zip = SOURCE / "normalized-required-stage.zip"
    assert sha256(source_zip.read_bytes()) == artifacts[source_zip.name]["sha256"]
    changes = []
    with ZipFile(source_zip) as z:
        for name in z.namelist():
            assert name.startswith("data/") and ".." not in Path(name).parts
            target = output / name
            before = target.read_bytes()
            after = z.read(name)
            if before != after:
                changes.append(dict(path=name, before_sha256=sha256(before),
                                    after_sha256=sha256(after)))
                target.write_bytes(after)
    # Reuse the accepted647-window stage to fill only its five source-qualified
    # OT catalog facts. Earlier107catalog blanks are not source-reported zeroes.
    import pandas as pd
    catalog_path = output / "data/raw/games/2026-27_regular_season.csv"
    catalog = pd.read_csv(catalog_path)
    periods_path = output / "data/raw/team_game_period_stats/2026-27_regular_season.csv"
    periods = pd.read_csv(periods_path)
    accepted_ot = set(periods.loc[periods.period_family.eq("overtime"), "game_id"])
    assert accepted_ot == {22600110, 22600120, 22600128, 22600141, 22600165}
    old_catalog_path = E.parent / "rollover-2026-27/current-refresh-20261104/summary-catalog.json"
    original_catalog_raw = old_catalog_path.read_bytes()
    original_catalog = json.loads(original_catalog_raw)
    metadata_changes = []
    for gid in sorted(accepted_ot):
        fact = original_catalog[f"{gid:010d}"]
        assert fact["periods"] == 5
        mask = catalog.game_id.eq(gid)
        before = catalog.loc[mask, "overtime_periods"].item()
        assert pd.isna(before)
        catalog.loc[mask, "overtime_periods"] = 1
        metadata_changes.append(dict(game_id=gid, field="overtime_periods", before=None, after=1,
                                     accepted_window_source_sha256=sha256(periods_path.read_bytes()),
                                     summary_catalog_sha256=sha256(original_catalog_raw),
                                     original_summary_sha256=fact["summary_sha256"]))
    catalog.to_csv(catalog_path, index=False)
    _safe_contracts(output, "2026-27", "Regular Season")
    validate_publication(output / "data")
    report = build_slice_manifest("2026-27", "Regular Season", data_root=output / "data",
                                  generation_id=VERSION)
    failures = {r["name"]: r["validation"]["errors"] for r in report["datasets"]
                if r["validation"]["errors"]}
    assert failures == {"player_game_period_stats": ["coverage missing 2208 requested keys"],
                        "team_game_period_stats": ["coverage missing 196 requested keys"]}
    qraw = (SOURCE / "qualification.json").read_bytes()
    evidence = dict(reference=str((SOURCE / "qualification.json").relative_to(ROOT)),
                    source_sha256=sha256(qraw), sha256=sha256(json.dumps(report, sort_keys=True).encode()))
    ids = intake_report(backlog, report, evidence)
    # Old roles/Advanced coverage failures no longer apply to this new version;
    # original exception records and old snapshot inventories remain unchanged.
    old_doc = json.loads((output / MANIFEST).read_bytes())
    carry = []
    for ident in old_doc["exceptions"]:
        item = backlog / (ident + ".json")
        if item.exists() and json.loads(item.read_bytes()).get("dataset") in {
                "player_game_starter_roles", "player_season_advanced",
                "team_game_period_stats", "player_game_period_stats"}:
            continue
        carry.append(ident)
    report_path = "data/metadata/required-current-validation.json"
    report_sha = write_json(output / report_path, report)
    write_json(output / "data/metadata/required-current-custody.json", dict(
        parent_development_manifest_sha256=parent_sha, source_stage_sha256=sha256(source_zip.read_bytes()),
        qualified_source_receipt_sha256=sha256(qraw), changed_files=changes,
        accepted_old_ot_metadata_changes=metadata_changes,
        production_writes=0, full_snapshot_accepted=False,
        new_standard_player_period_keys_missing=2208, new_team_period_keys_missing=196,
        all_source_team_windows_required=745, new_ot_player_keys="unknown pending actual source windows",
        old_484_rate_unknowns_preserved=True))
    doc = dict(old_doc, version=VERSION,
               scope="123 due games at2026-11-07T03:46:21.725918Z; source-qualified roles/catalog and selected season facts; ID18 fullLAL9 Rest0 retained; periods/rate numerical/freshness/production acceptance incomplete",
               source_evidence=dict(reference=evidence["reference"], sha256=sha256(qraw)),
               exceptions=sorted(set(carry + ids)),
               validation_reports=[dict(path=report_path, sha256=report_sha, state=report["validation_state"])])
    doc["files"] = {p.relative_to(output).as_posix(): sha256(p.read_bytes())
                    for p in sorted((output / "data").rglob("*"))
                    if p.is_file() and p.relative_to(output) != MANIFEST}
    digest = write_json(output / MANIFEST, doc)
    DevelopmentSnapshot(output, digest)
    return digest, report


if __name__ == "__main__":
    import sys
    print(compose(Path(sys.argv[1]), Path(sys.argv[2]))[0])
