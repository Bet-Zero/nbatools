"""One immutable scorer-bound period correction, using existing validation/versioning."""

import csv
import io
import json
from fractions import Fraction
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from nbatools.commands.validation_control import build_slice_manifest
from nbatools.development_data import MANIFEST, DevelopmentSnapshot, sha256
from tools.development_snapshot import _safe_contracts, write_json

E = Path(__file__).resolve().parent
SUFFIX = "2026-27_regular_season.csv"
VERSION = "current123-period-scorer-development-v5"
BOOK_SHA = "5d11d1974ca1426afda19575cc9a8af316d5a9471f26ced48f8470bbaf830b2b"
COUNT_FACTS = [
    ("player", "quarter", "2", "dreb", 0, 1, 2),
    ("player", "quarter", "2", "reb", 0, 1, 2),
    ("player", "half", "first", "dreb", 1, 2, 3),
    ("player", "half", "first", "reb", 3, 4, 3),
    ("team", "quarter", "2", "dreb", 5, 6, 2),
    ("team", "quarter", "2", "reb", 7, 8, 2),
    ("team", "half", "first", "dreb", 10, 11, 3),
    ("team", "half", "first", "reb", 19, 20, 3),
]


def apply(output, rate_oracle=None, expected_rate_sha256=None):
    """Absent independent exposure proof, the 38 dependent REB% cells stay unknown."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    binding = json.loads((E / "binding.json").read_bytes())
    source = E / binding["archive"]
    assert sha256(source.read_bytes()) == binding["archive_sha256"]
    root = output / "stage"
    with ZipFile(source) as z:
        assert all(n.startswith("data/") and ".." not in Path(n).parts for n in z.namelist())
        z.extractall(root)
    prior = DevelopmentSnapshot(root, binding["manifest_sha256"])
    book_dir = E / "hosted-initial/acquired_data/current123-game184-book"
    book = book_dir / (BOOK_SHA + ".pdf")
    assert sha256(book.read_bytes()) == BOOK_SHA
    capture = json.loads((book_dir / "capture.json").read_bytes())
    assert capture["sha256"] == BOOK_SHA and capture["http_status"] == 200 and capture["pdf_parsed"]
    assert capture["game_id"] == "0022600184" and capture["attempts"] == 1
    rebound_rates = None
    rebound_details = {}
    if rate_oracle is not None:
        raw = Path(rate_oracle).read_bytes()
        assert expected_rate_sha256 and sha256(raw) == expected_rate_sha256
        proof = json.loads(raw)
        assert proof["pdf_sha256"] == BOOK_SHA and proof["qualified_reb_pct_cells"] == 38
        rebound_rates = {}
        for fact in proof["rates"]:
            assert fact["game_id"] == 22600184 and fact["window"] in {"q2", "h1"}
            assert 0 <= fact["numerator"] <= fact["denominator"] and fact["denominator"] > 0
            exact = Fraction(fact["numerator"], fact["denominator"])
            assert abs(float(exact) - fact["reb_pct"]) < 1e-14
            window = ("quarter", "2") if fact["window"] == "q2" else ("half", "first")
            key = fact["team_id"], fact["player_id"], *window
            assert key not in rebound_rates
            rebound_rates[key] = float(exact)
            rebound_details[key] = {
                name: fact[name] for name in ("numerator", "denominator", "exact")
            }
        assert len(rebound_rates) == 38
        fields = {"reboundsDefensive": "dreb", "reboundsTotal": "reb"}
        windows = {"q2": ("quarter", "2"), "h1": ("half", "first")}
        observed_counts = set()
        for fact in proof["count_corrections"]:
            assert fact["game_id"] == 22600184 and fact["team_id"] == 1610612742
            assert fact.get("player_id", 1629023) == 1629023
            observed_counts.add(
                (
                    fact["dataset"],
                    *windows[fact["window"]],
                    fields[fact["field"]],
                    fact["before"],
                    fact["after"],
                )
            )
        assert observed_counts == {row[:6] for row in COUNT_FACTS}
        write_json(root / "data/metadata/corrections/game184-rebound-oracle.json", proof)
    changes, rate_ledger, file_changes = [], [], []
    for grain in ("player", "team"):
        path = root / f"data/raw/{grain}_game_period_stats/{SUFFIX}"
        before = path.read_bytes()
        lines = before.decode().splitlines(keepends=True)
        records = list(csv.reader(io.StringIO(before.decode())))
        assert len(records) == len(lines), "Multiline CSV requires the existing full parser"
        header = records[0]
        indexes = {name: i for i, name in enumerate(header)}
        touched = set()
        for row_index, cells in enumerate(records[1:], 1):
            row = dict(zip(header, cells, strict=True))
            if int(row["game_id"]) != 22600184:
                continue
            eligible_player = grain == "team" or int(row["player_id"]) == 1629023
            if eligible_player and int(row["team_id"]) == 1610612742:
                for g, family, value, field, old, new, page in COUNT_FACTS:
                    if (grain, row["period_family"], row["period_value"]) != (g, family, value):
                        continue
                    column = indexes[field]
                    assert float(cells[column]) == old
                    changes.append(
                        dict(
                            dataset=grain,
                            row=row_index - 1,
                            key={
                                k: row[k]
                                for k in [
                                    "game_id",
                                    "team_id",
                                    *(["player_id"] if grain == "player" else []),
                                    "period_family",
                                    "period_value",
                                ]
                            },
                            field=field,
                            before_token=cells[column],
                            after_token=str(new),
                            book_sha256=BOOK_SHA,
                            zero_based_book_page=page,
                        )
                    )
                    cells[column] = str(new)
                    touched.add(row_index)
            # Existing count->rate dependency policy applies to the ENTIRE window.
            affected_window = (row["period_family"], row["period_value"]) in {
                ("quarter", "2"),
                ("half", "first"),
            }
            if grain == "player" and affected_window:
                key = (
                    int(row["team_id"]),
                    int(row["player_id"]),
                    row["period_family"],
                    row["period_value"],
                )
                value = None if rebound_rates is None else rebound_rates[key]
                old = cells[indexes["reb_pct"]]
                cells[indexes["reb_pct"]] = "" if value is None else str(value)
                rate_ledger.append(
                    dict(
                        key=list(key),
                        field="reb_pct",
                        independent_exposure=rebound_details.get(key),
                        before_token=old,
                        after_token=cells[indexes["reb_pct"]],
                        method="independently derived scorer rebound exposure"
                        if value is not None
                        else "withheld pending independent scorer rebound exposure",
                    )
                )
                touched.add(row_index)
        for row_index in touched:
            buffer = io.StringIO(newline="")
            csv.writer(buffer, lineterminator="\n").writerow(records[row_index])
            lines[row_index] = buffer.getvalue()
        path.write_text("".join(lines))
        assert path.read_bytes() != before
        file_changes.append(
            dict(
                path=path.relative_to(root).as_posix(),
                before_sha256=sha256(before),
                after_sha256=sha256(path.read_bytes()),
                touched_rows=len(touched),
            )
        )
    assert len(changes) == 8 and len(rate_ledger) == 38
    _safe_contracts(root, "2026-27", "Regular Season")
    report = build_slice_manifest(
        "2026-27", "Regular Season", data_root=root / "data", generation_id=VERSION
    )
    assert report["validation_state"] == "passed"
    players = pd.read_csv(root / f"data/raw/player_game_period_stats/{SUFFIX}")
    assert players[["usg_pct", "tov_pct"]].isna().sum().to_dict() == {
        "usg_pct": 242,
        "tov_pct": 242,
    }
    # Whole/core and all unrelated raw/processed/reason/source inputs stay pinned.
    for path, digest in prior.files.items():
        if path not in {r["path"] for r in file_changes}:
            assert sha256((root / path).read_bytes()) == digest
    correction = dict(
        parent_manifest_sha256=binding["manifest_sha256"],
        book_sha256=BOOK_SHA,
        book_identity="2026-11-04 DAL111@SAS112; official whole/Q2/H1 scorer and Q2 05:14 rebound",
        count_changes=changes,
        rate_changes=rate_ledger,
        file_changes=file_changes,
        independent_rate_oracle_sha256=expected_rate_sha256,
        old484_rate_unknowns_preserved=True,
        source_originals_changed=False,
        production_writes=0,
        full_snapshot_accepted=False,
    )
    write_json(output / "book-correction.json", correction)
    write_json(root / "data/metadata/period-book-correction.json", correction)
    report_path = "data/metadata/period-book-validation.json"
    report_sha = write_json(root / report_path, report)
    doc = dict(
        prior.document,
        version=VERSION,
        scope=(
            "Fixed123-game cutoff; all745period windows and game184 scorer rebound correction; "
            "old484rate facts/membership/current-freshness/production acceptance remain open"
        ),
        source_evidence=dict(
            reference="working/nba-tools-completion-program/source-evidence/current123-periods-20261107/hosted-initial/acquired_data/current123-game184-book/"
            + BOOK_SHA
            + ".pdf",
            sha256=BOOK_SHA,
        ),
        validation_reports=[dict(path=report_path, sha256=report_sha, state="passed")],
    )
    if rebound_rates is not None:
        doc["exceptions"] = [
            ident
            for ident in doc["exceptions"]
            if ident != "DQ-auto-4294464123002d61e11cd59f7cdebfd1690b172d28b608f26d934e725ecc6c7a"
        ]
    # Without a complete independent rate proof, keep that evidence gap explicit.
    doc["files"] = {
        p.relative_to(root).as_posix(): sha256(p.read_bytes())
        for p in sorted((root / "data").rglob("*"))
        if p.is_file() and p.relative_to(root) != MANIFEST
    }
    digest = write_json(root / MANIFEST, doc)
    DevelopmentSnapshot(root, digest)
    archive = output / "current123-period-v5.zip"
    with ZipFile(archive, "x", ZIP_DEFLATED) as z:
        for path in sorted((root / "data").rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(root).as_posix())
    result = dict(
        archive=archive.name,
        archive_sha256=sha256(archive.read_bytes()),
        manifest_sha256=digest,
        parent_manifest_sha256=binding["manifest_sha256"],
        book_sha256=BOOK_SHA,
        production_writes=0,
        full_snapshot_accepted=False,
    )
    write_json(output / "v5-binding.json", result)
    return result, correction
