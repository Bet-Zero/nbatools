"""Compose pinned participation overlays offline; never choose conflicting authority.

The result is an overlay, not a generation or publication receipt. A complete
source root must still pass the existing source-replay validator and consumer gate.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

import pandas as pd

from nbatools.commands import _reported_absence_reasons as reasons
from nbatools.commands.pipeline.pull_player_game_availability import _game_digest
from tools.availability_overlay import _indexed, _table, _unique_object, binding, verify_append

_TABLE = re.compile(
    r"raw/(player_game_availability|player_game_absence_reasons)/"
    r"(?:19|20)\d{2}-\d{2}_(?:regular_season|playoffs)\.(?:csv|imports\.json)"
)
_SOURCE = re.compile(
    r"raw/player_game_(?:availability|absence_reason)_sources/[\w.-]+\.(?:json|pdf)"
)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw):
    return json.loads(raw, object_pairs_hook=_unique_object)


def _path(relative):
    path = PurePosixPath(relative)
    if (
        not isinstance(relative, str)
        or str(path) != relative
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in relative
    ):
        raise ValueError("Unsafe archive or baseline path")
    return relative


def _metadata(relative, raw):
    return dict(path=relative, sha256=_sha(raw), size_bytes=len(raw))


def _csv(header, rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


def _merge(old, new):
    if any(
        key in old and json.dumps(old[key], sort_keys=True) != json.dumps(value, sort_keys=True)
        for key, value in new.items()
    ):
        raise ValueError("Conflicting serialized observation or import authority")
    return old | new


def _check_creations(relative, raw, spec):
    reason = relative.startswith(reasons.DIRECTORY)
    field = "added_observation_keys" if reason else "added_game_ids"
    if (
        set(spec) != {"base_presence", field, "added_records"}
        or spec["base_presence"] != "manifest_absent"
    ):
        raise ValueError("Invalid manifest-absent creation metadata")
    if relative.endswith(".csv"):
        _, rows = _table(raw)
        _indexed(rows)
        actual = (
            {reasons.key(row) for row in rows}
            if reason
            else {f"{int(r['game_id']):010d}" for r in rows}
        )
        count = len(rows)
    else:
        ledger = _json(raw)
        actual = set(ledger) if reason else {f"{int(g):010d}" for g in ledger}
        count = len(ledger)
    if (
        not isinstance(spec[field], list)
        or len(set(spec[field])) != len(spec[field])
        or set(spec[field]) != actual
        or type(spec["added_records"]) is not int
        or spec["added_records"] != count
        or not count
    ):
        raise ValueError("Manifest-absent population differs from declared scope")


def _check_authority(rows, ledger):
    frame = pd.DataFrame(rows)
    if set(ledger) != {str(int(g)) for g in frame.game_id}:
        raise ValueError("Availability group/import population differs")
    for gid, group in frame.groupby(pd.to_numeric(frame.game_id)):
        if ledger[str(gid)]["sha256"] != _game_digest(group):
            raise ValueError("Composed game population changes import authority digest")


def compose_overlays(
    packages: list[tuple[Path, str]],
    baseline_root: Path,
    output: Path,
    *,
    base_generation: str,
    base_manifest_sha256: str,
    candidate_sha: str,
) -> dict:
    """Merge exact cells/import objects against actual manifest-bound BASE bytes.

    ``packages`` contains independently accepted artifact ZIPs and their SHA256s.
    Acceptance is external evidence; this function checks composition/preservation,
    not fresh source qualification. Only declared raw paths plus validation.json
    are exported. The baseline is read-only and the output must be a new directory.
    """
    if (
        not packages
        or not re.fullmatch(r"[a-f0-9]{40}", candidate_sha)
        or output.exists()
        or baseline_root.is_symlink()
        or output.resolve() == baseline_root.resolve()
        or baseline_root.resolve() in output.resolve().parents
        or output.resolve() in baseline_root.resolve().parents
    ):
        raise ValueError("Composition requires pinned packages and separate new output")
    manifest_path = baseline_root / "metadata/generation_manifest.json"
    if manifest_path.is_symlink() or manifest_path.parent.is_symlink():
        raise ValueError("Symlink in BASE manifest path")
    manifest_raw = manifest_path.read_bytes()
    manifest = _json(manifest_raw)
    if _sha(manifest_raw) != base_manifest_sha256 or manifest["generation_id"] != base_generation:
        raise ValueError("BASE generation/manifest differs from requested binding")
    entries = {_path(item["path"]): item for item in manifest["files"]}
    if len(entries) != len(manifest["files"]):
        raise ValueError("Duplicate BASE manifest path")
    baseline, combined, inputs = {}, {}, []

    def base(relative):
        path = baseline_root / _path(relative)
        if any(p.is_symlink() for p in (path, *path.parents) if p != baseline_root.parent):
            raise ValueError("Symlink in BASE dependency")
        if relative not in entries:
            if path.exists():
                raise ValueError("Manifest-absent path has a configured BASE file")
            return None
        if relative not in baseline:
            raw = path.read_bytes()
            if any(entries[relative].get(k) != v for k, v in _metadata(relative, raw).items()):
                raise ValueError("Actual BASE bytes differ from immutable manifest")
            baseline[relative] = raw
        return baseline[relative]

    declared_tables, total_members, total_bytes = set(), 0, 0
    seen_archives = set()
    for archive_path, expected_sha in sorted(packages, key=lambda item: item[1]):
        if archive_path.stat().st_size > 20_000_000:
            raise ValueError("Package ZIP exceeds byte bound")
        archive_raw = archive_path.read_bytes()
        if (
            archive_path.is_symlink()
            or not re.fullmatch(r"[a-f0-9]{64}", expected_sha)
            or _sha(archive_raw) != expected_sha
        ):
            raise ValueError("Pinned package ZIP bytes differ")
        if expected_sha in seen_archives:
            continue
        seen_archives.add(expected_sha)
        with ZipFile(io.BytesIO(archive_raw)) as archive:
            names = [_path(info.filename.rstrip("/")) for info in archive.infolist()]
            total_members += len(names)
            total_bytes += sum(info.file_size for info in archive.infolist())
            if (
                len(set(names)) != len(names)
                or total_members > 2000
                or total_bytes > 100_000_000
                or any(
                    info.file_size > 20_000_000 or (info.external_attr >> 16) & 0o170000 == 0o120000
                    for info in archive.infolist()
                )
            ):
                raise ValueError("Unsafe, duplicate or oversized artifact members")
            validations = [name for name in names if PurePosixPath(name).name == "validation.json"]
            if len(validations) != 1:
                raise ValueError("Artifact must contain exactly one validation manifest")
            member = validations[0]
            validation_raw = archive.read(member)
            document = _json(validation_raw)
            if (
                document["base_generation"] != base_generation
                or document["base_manifest_sha256"] != base_manifest_sha256
                or document.get("publication_state") != "staged_only_no_writes"
                or document.get("production_writes", 0) != 0
            ):
                raise ValueError("Overlay BASE or staging authority differs")
            nested = document.get("season_stage_validations", [])
            if not isinstance(nested, list):
                raise ValueError("Invalid nested season-stage bindings")
            for bound in [document, *nested]:
                if (
                    bound["base_generation"] != base_generation
                    or bound["base_manifest_sha256"] != base_manifest_sha256
                ):
                    raise ValueError("Nested stage BASE binding differs")
                for relative, digest in bound.get("base_file_hashes", {}).items():
                    if relative not in entries or entries[relative]["sha256"] != digest:
                        raise ValueError("Package BASE dependency metadata differs")
            files = document["overlay_files"]
            indexed = {item["path"]: item for item in files}
            append, creations = (
                document.get("append_only", {}),
                document.get("manifest_absent_creations", {}),
            )
            if len(indexed) != len(files) or append.keys() & creations.keys():
                raise ValueError("Duplicate overlay paths or contradictory change metadata")
            tables = {p for p in indexed if _TABLE.fullmatch(p)}
            if tables != append.keys() | creations.keys():
                raise ValueError("Every changed table requires exact append/absence metadata")
            if any(
                (
                    p.removesuffix(".csv") + ".imports.json"
                    if p.endswith(".csv")
                    else p.replace(".imports.json", ".csv")
                )
                not in tables
                for p in tables
            ):
                raise ValueError("Overlay CSV and imports must be jointly declared")
            package_tables = {}
            prefix = member.removesuffix("validation.json")
            for relative, item in indexed.items():
                _path(relative)
                if (
                    not (_TABLE.fullmatch(relative) or _SOURCE.fullmatch(relative))
                    or ".." in relative
                ):
                    raise ValueError("Overlay path is outside participation namespaces")
                raw = archive.read(prefix + relative)
                if item != _metadata(relative, raw):
                    raise ValueError("Overlay bytes differ from validation metadata")
                before = base(relative)
                if relative in tables:
                    package_tables[relative] = raw
                    declared_tables.add(relative)
                    partner = (
                        relative.removesuffix(".csv") + ".imports.json"
                        if relative.endswith(".csv")
                        else relative.replace(".imports.json", ".csv")
                    )
                    if (relative in entries) != (partner in entries):
                        raise ValueError("BASE CSV and imports must be jointly present or absent")
                    if before is not None:
                        if relative not in append:
                            raise ValueError("Existing BASE table requires append binding")
                        verify_append(relative, before, raw, append[relative])
                        if relative.endswith(".imports.json"):
                            _merge(_json(before), _json(raw))
                    else:
                        if relative not in creations:
                            raise ValueError("Absent BASE table requires creation binding")
                        _check_creations(relative, raw, creations[relative])
                    if relative.endswith(".csv"):
                        header, rows = _table(raw)
                        if relative in combined:
                            previous_header, previous = combined[relative]
                            if header != previous_header:
                                raise ValueError("Composition cannot change table schema/order")
                            combined[relative] = (header, _merge(previous, _indexed(rows)))
                        else:
                            combined[relative] = (header, _indexed(rows))
                    else:
                        combined[relative] = _merge(combined.get(relative, {}), _json(raw))
                else:
                    if (
                        before is not None
                        and raw != before
                        or relative in combined
                        and combined[relative] != raw
                    ):
                        raise ValueError("Conflicting retained source path/authority")
                    combined[relative] = raw
            for relative, raw in package_tables.items():
                if relative.startswith("raw/player_game_availability/") and relative.endswith(
                    ".csv"
                ):
                    _check_authority(
                        _table(raw)[1],
                        _json(package_tables[relative.removesuffix(".csv") + ".imports.json"]),
                    )
            inputs.append(
                dict(
                    archive_sha256=expected_sha,
                    archive_size_bytes=len(archive_raw),
                    validation_member=member,
                    validation_sha256=_sha(validation_raw),
                )
            )

    append, creations, payloads = {}, {}, {}
    for relative, value in sorted(combined.items()):
        if relative not in declared_tables:
            raw = value
        elif relative.endswith(".csv"):
            header, rows = value
            _indexed(list(rows.values()))
            # Keep original BASE row order and every original serialized cell.
            old = _indexed(_table(baseline[relative])[1]) if relative in baseline else {}
            raw = _csv(
                header, [*old.values(), *(rows[k] for k in sorted(rows.keys() - old.keys()))]
            )
        else:
            raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
        if relative in baseline and raw == baseline[relative]:
            continue
        payloads[relative] = raw
        if relative in declared_tables:
            reason = relative.startswith(reasons.DIRECTORY)
            records = combined[relative][1] if relative.endswith(".csv") else combined[relative]
            game_ids = (
                sorted({k[0] for k in records})
                if relative.endswith(".csv")
                else sorted(map(int, records))
                if not reason
                else []
            )
            if relative in baseline:
                before = baseline[relative]
                old = _indexed(_table(before)[1]) if relative.endswith(".csv") else _json(before)
                old_games = {k[0] for k in old} if relative.endswith(".csv") else set(map(int, old))
                append[relative] = binding(
                    before,
                    [f"{g:010d}" for g in sorted(set(game_ids) - old_games)],
                    added_records=len(records) - len(old),
                )
                verify_append(relative, before, raw, append[relative])
            else:
                field = "added_observation_keys" if reason else "added_game_ids"
                keys = (
                    sorted(reasons.key(row) for row in records.values())
                    if reason and relative.endswith(".csv")
                    else sorted(records)
                    if reason
                    else [f"{g:010d}" for g in game_ids]
                )
                creations[relative] = dict(
                    base_presence="manifest_absent", added_records=len(records), **{field: keys}
                )
                _check_creations(relative, raw, creations[relative])

    # Preserve every per-game authority digest; a partial group cannot adopt a
    # different packet or mutate a stronger report's qualified population.
    for relative in sorted(p for p in declared_tables if p.endswith(".csv")):
        frame = pd.DataFrame(list(combined[relative][1].values()))
        ledger = combined[relative.removesuffix(".csv") + ".imports.json"]
        if relative.startswith(reasons.DIRECTORY):
            source_metadata = {**entries, **{p: _metadata(p, raw) for p, raw in payloads.items()}}
            reasons.validate_rows(frame, ledger, source_entry=source_metadata.__getitem__)
            binary_path = relative.replace(reasons.DIRECTORY, "raw/player_game_availability/")
            binary_raw = payloads.get(binary_path) or base(binary_path)
            imports_raw = payloads.get(binary_path.removesuffix(".csv") + ".imports.json") or base(
                binary_path.removesuffix(".csv") + ".imports.json"
            )
            reasons.validate_identity_bindings(
                frame,
                ledger,
                pd.read_csv(io.BytesIO(binary_raw), dtype=str, keep_default_na=False),
                _json(imports_raw),
            )
        else:
            _check_authority(frame.to_dict("records"), ledger)
    result = dict(
        candidate_sha=candidate_sha,
        base_generation=base_generation,
        base_manifest_sha256=base_manifest_sha256,
        input_packages=inputs,
        base_file_hashes={p: _sha(raw) for p, raw in sorted(baseline.items())},
        append_only=append,
        manifest_absent_creations=creations,
        overlay_files=[_metadata(p, raw) for p, raw in sorted(payloads.items())],
        composition_preservation_checked=True,
        input_base_dependency_metadata_checked=True,
        baseline_byte_checks_scope="touched paths only; caller checks other dependencies",
        source_replay_validation_complete=False,
        publication_state="staged_only_no_writes",
        full_required_slice_accepted=False,
        production_writes=0,
    )
    output.mkdir(parents=True)
    for relative, raw in payloads.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    (output / "validation.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result
