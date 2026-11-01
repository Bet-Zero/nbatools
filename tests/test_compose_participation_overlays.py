"""Composition preserves qualified inputs; fixtures are not NBA source evidence."""

import copy
import csv
import hashlib
import io
import json
import warnings
from zipfile import ZipFile, ZipInfo

import pandas as pd
import pytest

from nbatools.commands import _reported_absence_reasons as reasons
from nbatools.commands.pipeline.pull_player_game_availability import COLUMNS, _game_digest
from tools.availability_overlay import binding
from tools.compose_participation_overlays import compose_overlays

pytestmark = pytest.mark.engine
CSV = "raw/player_game_availability/2025-26_regular_season.csv"
IMPORTS = CSV.replace(".csv", ".imports.json")
SOURCE = "raw/player_game_availability_sources/"
REASONS = "raw/player_game_absence_reasons/2025-26_regular_season.csv"
GENERATION = "composition-fixture"
CANDIDATE = "a" * 40


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def table(rows, header=COLUMNS):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode()


def person(gid, pid, *, played=False, season="2025-26"):
    return dict(
        zip(
            COLUMNS,
            [
                f"{gid:010d}",
                "2025-10-21",
                season,
                "Regular Season",
                "1",
                "AAA",
                str(pid),
                f"Fixture Player {pid}",
                "played" if played else "did_not_play",
                "21.299999999999997" if played else "",
                "literal, controlled\nfixture",
                "nba_official_finalbox:controlled"
                if played
                else "nba_stats_structured_archive:controlled",
                "b" * 64,
                "",
                "listed_player_rows_only",
            ],
        )
    )


def imported(rows, source="structured"):
    return {
        str(g): dict(
            source=source,
            sha256=_game_digest(pd.DataFrame([r for r in rows if int(r["game_id"]) == g])),
            imported_team_ids=[1],
        )
        for g in {int(r["game_id"]) for r in rows}
    }


@pytest.fixture
def preparation(tmp_path):
    baseline = tmp_path / "baseline"
    old = [person(22500002, 11, played=True), person(22500002, 12)]
    old_import = imported(old, "report")
    originals = {
        CSV: table(old),
        IMPORTS: json.dumps(old_import).encode(),
        SOURCE + "old.pdf": b"%PDF-controlled-old",
    }
    for relative, raw in originals.items():
        path = baseline / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    manifest = json.dumps(
        dict(
            generation_id=GENERATION,
            files=[
                dict(path=p, sha256=sha(raw), size_bytes=len(raw)) for p, raw in originals.items()
            ],
        )
    ).encode()
    meta = baseline / "metadata/generation_manifest.json"
    meta.parent.mkdir()
    meta.write_bytes(manifest)
    counter = 0

    def package(new, *, csv_path=CSV, ledger=None, extras=None, mutate=None, extra_member=None):
        nonlocal counter
        counter += 1
        existing = old if csv_path == CSV else []
        rows = [*existing, *new]
        imports = (
            {**(old_import if existing else {}), **imported(new)} if ledger is None else ledger
        )
        partner = csv_path.replace(".csv", ".imports.json")
        payloads = {csv_path: table(rows), partner: json.dumps(imports).encode(), **(extras or {})}
        games = sorted({r["game_id"] for r in new})
        if existing:
            append = {
                p: binding(originals[p], games, added_records=n)
                for p, n in [(csv_path, len(new)), (partner, len(games))]
            }
            creations = {}
        else:
            append = {}
            creations = {
                p: dict(base_presence="manifest_absent", added_game_ids=games, added_records=n)
                for p, n in [(csv_path, len(new)), (partner, len(games))]
            }
        for p, raw in (extras or {}).items():
            if p.startswith(reasons.DIRECTORY):
                data = (
                    list(csv.DictReader(io.StringIO(raw.decode())))
                    if p.endswith(".csv")
                    else json.loads(raw)
                )
                keys = sorted(reasons.key(r) for r in data) if p.endswith(".csv") else sorted(data)
                creations[p] = dict(
                    base_presence="manifest_absent",
                    added_observation_keys=keys,
                    added_records=len(data),
                )
        validation = dict(
            base_generation=GENERATION,
            base_manifest_sha256=sha(manifest),
            publication_state="staged_only_no_writes",
            production_writes=0,
            append_only=append,
            manifest_absent_creations=creations,
            overlay_files=[
                dict(path=p, sha256=sha(raw), size_bytes=len(raw)) for p, raw in payloads.items()
            ],
        )
        if mutate:
            mutate(validation, payloads)
        path = tmp_path / f"package{counter}.zip"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with ZipFile(path, "w") as archive:
                archive.writestr("stage/validation.json", json.dumps(validation))
                for p, raw in payloads.items():
                    archive.writestr("stage/" + p, raw)
                if extra_member:
                    archive.writestr(*extra_member)
        return path, sha(path.read_bytes())

    def compose(packages, name="output"):
        return compose_overlays(
            packages,
            baseline,
            tmp_path / name,
            base_generation=GENERATION,
            base_manifest_sha256=sha(manifest),
            candidate_sha=CANDIDATE,
        )

    return dict(
        root=baseline,
        old=old,
        old_import=old_import,
        originals=originals,
        package=package,
        compose=compose,
        tmp=tmp_path,
    )


def _reason(row, imports):
    source, receipt = b"%PDF-controlled-reason-fixture", b"{}"
    source_path = reasons.SOURCES + sha(source) + ".pdf"
    receipt_path = reasons.SOURCES + sha(receipt) + ".receipt.json"
    fact = dict(
        game_id=row["game_id"],
        game_date=row["game_date"],
        season=row["season"],
        season_type=row["season_type"],
        team_id=row["team_id"],
        player_id=row["player_id"],
        player_name=row["player_name"],
        reported_reason="reported_rest",
        reason_text="Rest",
        source_kind="nba_official_finalbox",
        source_url="https://statsdmz.nba.com/pdfs/fixture.pdf",
        source_sha256=sha(source),
        source_locator="{}",
        identity_source_sha256=row["source_sha256"],
        coverage_scope=reasons.SCOPE,
    )
    lineage = {
        reasons.key(fact): dict(
            row_sha256=reasons.row_digest(fact),
            identity_import=imports[str(int(row["game_id"]))],
            source_file=dict(path=source_path, sha256=sha(source), size_bytes=len(source)),
            source_receipt=dict(path=receipt_path, sha256=sha(receipt), size_bytes=len(receipt)),
        )
    }
    return {
        REASONS: table([fact], reasons.COLUMNS),
        REASONS.replace(".csv", ".imports.json"): json.dumps(lineage).encode(),
        source_path: source,
        receipt_path: receipt,
    }


def test_union_preserves_cells_pdf_authority_dependencies_and_reason_lineage(preparation):
    p = preparation
    a, b = person(22500003, 21), person(22500004, 22)
    package_a = p["package"]([a], extras={SOURCE + "a.json": b"original-A"})
    package_b = p["package"]([b], extras={SOURCE + "b.json": b"original-B"})
    historical = p["package"](
        [person(22400005, 23, season="2024-25")], csv_path=CSV.replace("2025-26", "2024-25")
    )
    dependency = p["package"](
        [a], extras={SOURCE + "a.json": b"original-A", **_reason(a, imported([a]))}
    )
    before = {f: f.read_bytes() for f in p["root"].rglob("*") if f.is_file()}
    inputs = [package_a, package_b, historical, dependency]
    result = p["compose"](inputs)
    reverse = p["compose"](list(reversed(inputs)), name="reversed")
    assert result == reverse
    assert result["append_only"][CSV]["added_records"] == 2
    assert result["append_only"][IMPORTS]["added_records"] == 2
    assert result["manifest_absent_creations"][REASONS]["added_records"] == 1
    assert not result["source_replay_validation_complete"] and result["production_writes"] == 0
    out = p["tmp"] / "output"
    rows = list(csv.DictReader(io.StringIO((out / CSV).read_text())))
    assert rows[:2] == p["old"] and [r["player_id"] for r in rows[2:]] == ["21", "22"]
    ledger = json.loads((out / IMPORTS).read_bytes())
    assert ledger["22500002"] == p["old_import"]["22500002"]
    assert len(rows) == 4 and len(ledger) == 3 and len(result["overlay_files"]) == 10
    assert before == {f: f.read_bytes() for f in before}
    assert all(
        (out / r["path"]).read_bytes() == (p["tmp"] / "reversed" / r["path"]).read_bytes()
        for r in result["overlay_files"]
    )


@pytest.mark.parametrize(
    "damage",
    [
        "old_cell",
        "old_authority_type",
        "new_cell",
        "new_authority",
        "source_path",
        "source_base",
        "partial_group",
    ],
)
def test_conflicting_or_partial_facts_fail_before_export(preparation, damage):
    p = preparation
    a = person(22500003, 21)
    first = p["package"]([a], extras={SOURCE + "shared.json": b"first"})
    changed = copy.deepcopy(a)
    imports = {**p["old_import"], **imported([a])}
    extras = {}
    mutate = None
    if damage == "old_cell":

        def mutate(v, files):
            raw = files[CSV].replace(b"21.299999999999997", b"21.3")
            files[CSV] = raw
            v["overlay_files"][0].update(sha256=sha(raw), size_bytes=len(raw))
    elif damage == "old_authority_type":
        imports["22500002"]["imported_team_ids"] = [True]
    elif damage == "new_cell":
        a["source_minutes"] = "0"
        first = p["package"]([a])
        changed["source_minutes"] = "0.0"
        imports = {**p["old_import"], **imported([a])}
    elif damage == "new_authority":
        imports["22500003"]["source"] = "report"
    elif damage == "source_path":
        extras[SOURCE + "shared.json"] = b"different"
    elif damage == "source_base":
        extras[SOURCE + "old.pdf"] = b"replacement"
    else:
        imports = {**p["old_import"], **imported([a, person(22500003, 99)])}
    second = p["package"]([changed], ledger=imports, extras=extras, mutate=mutate)
    with pytest.raises(ValueError):
        p["compose"]([first, second])
    assert not (p["tmp"] / "output").exists()


@pytest.mark.parametrize(
    "damage",
    [
        "base_bytes",
        "base_binding",
        "base_generation",
        "base_hash",
        "partial_pair",
        "unregistered_table",
        "wrong_count",
        "source_metadata",
        "creation_stray",
        "creation_partial_base",
        "nested_base_generation",
        "nested_base_manifest",
        "nested_dependency",
    ],
)
def test_base_manifest_scope_and_change_metadata_are_required(preparation, damage):
    p = preparation
    creation = damage.startswith("creation")
    path = CSV.replace("2025-26", "2024-25") if creation else CSV

    def mutate(v, files):
        if damage.startswith("nested_"):
            nested = dict(
                base_generation=GENERATION,
                base_manifest_sha256=v["base_manifest_sha256"],
                base_file_hashes={CSV: sha(p["originals"][CSV])},
            )
            if damage == "nested_base_generation":
                nested["base_generation"] = "other"
            elif damage == "nested_base_manifest":
                nested["base_manifest_sha256"] = "0" * 64
            else:
                nested["base_file_hashes"][CSV] = "0" * 64
            v["season_stage_validations"] = [nested]
        elif damage == "base_binding":
            v["append_only"][CSV]["base_sha256"] = "0" * 64
        elif damage == "base_generation":
            v["base_generation"] = "other"
        elif damage == "base_hash":
            v["base_manifest_sha256"] = "0" * 64
        elif damage == "partial_pair":
            files.pop(IMPORTS)
            v["append_only"].pop(IMPORTS)
            v["overlay_files"] = [i for i in v["overlay_files"] if i["path"] != IMPORTS]
        elif damage == "unregistered_table":
            v["append_only"].pop(CSV)
        elif damage == "wrong_count":
            v["append_only"][CSV]["added_records"] = 2
        elif damage == "source_metadata":
            v["overlay_files"][0]["size_bytes"] += 1
        elif damage == "creation_partial_base":
            target = p["root"] / path
            target.write_bytes(b"stray")
            manifest_path = p["root"] / "metadata/generation_manifest.json"
            value = json.loads(manifest_path.read_bytes())
            value["files"].append(dict(path=path, sha256=sha(b"stray"), size_bytes=5))
            manifest_path.write_text(json.dumps(value))
            v["base_manifest_sha256"] = sha(manifest_path.read_bytes())

    package = p["package"](
        [
            person(
                22400003 if creation else 22500003, 21, season="2024-25" if creation else "2025-26"
            )
        ],
        csv_path=path,
        mutate=mutate,
    )
    if damage == "base_bytes":
        (p["root"] / CSV).write_bytes(b"changed BASE")
    elif damage == "creation_stray":
        (p["root"] / path).write_bytes(b"stray")
    with pytest.raises(ValueError):
        if damage == "creation_partial_base":
            compose_overlays(
                [package],
                p["root"],
                p["tmp"] / "output",
                base_generation=GENERATION,
                base_manifest_sha256=sha(
                    (p["root"] / "metadata/generation_manifest.json").read_bytes()
                ),
                candidate_sha=CANDIDATE,
            )
        else:
            p["compose"]([package])
    assert not (p["tmp"] / "output").exists()


@pytest.mark.parametrize("damage", ["traversal", "duplicate", "symlink", "zip_hash"])
def test_unsafe_or_unpinned_archives_are_rejected(preparation, damage):
    p = preparation
    if damage == "symlink":
        item = ZipInfo("stage/link")
        item.external_attr = 0o120777 << 16
        extra = (item, b"/outside")
    elif damage == "duplicate":
        extra = ("stage/" + CSV, b"duplicate")
    else:
        extra = ("../outside", b"invalid") if damage == "traversal" else None
    package = p["package"]([person(22500003, 21)], extra_member=extra)
    if damage == "zip_hash":
        package = (package[0], "0" * 64)
    with pytest.raises(ValueError):
        p["compose"]([package])
    assert not (p["tmp"] / "output").exists()


def test_reason_lineage_cannot_adopt_another_game_import(preparation):
    p = preparation
    row = person(22500003, 21)
    imports = imported([row])
    extras = _reason(row, imports)
    lineage_path = REASONS.replace(".csv", ".imports.json")
    lineage = json.loads(extras[lineage_path])
    next(iter(lineage.values()))["identity_import"]["source"] = "report"
    extras[lineage_path] = json.dumps(lineage).encode()
    package = p["package"]([row], extras=extras)
    with pytest.raises(ValueError, match="import lineage changed"):
        p["compose"]([package])
    assert not (p["tmp"] / "output").exists()


def test_duplicate_archive_dependency_deduplicates_after_hash_check(preparation):
    p = preparation
    package = p["package"]([person(22500003, 21)])
    result = p["compose"]([package, package])
    assert len(result["input_packages"]) == 1
    assert result["append_only"][CSV]["added_records"] == 1


def test_source_namespace_does_not_accept_executable_payloads(preparation):
    p = preparation
    package = p["package"](
        [person(22500003, 21)], extras={SOURCE + "payload.py": b"not source evidence"}
    )
    with pytest.raises(ValueError, match="outside participation namespaces"):
        p["compose"]([package])
    assert not (p["tmp"] / "output").exists()
