"""One immutable whole-game rebound correction: v6 -> new v7, v6 kept unchanged.

Scope: player_game_stats row 0022600184 / PID 1629023 / DAL changes exactly
DREB 5->6 and REB 9->10 (OREB 4 already matches). Evidence is the already
retained official scorer FINAL BOX (PDF sha 5d11d197...) and the PR602-reviewed
independent oracle (sha 7d054703...). No source is collected again.

Uses the existing development-snapshot pieces (DevelopmentSnapshot hash
authentication, _safe_contracts, build_slice_manifest, the pure player feature
builder) the same way the accepted v5/v6 preparations did. Every file other than
the one raw CSV and the new metadata stays byte-identical; no production write.
"""

import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from nbatools.commands.validation_control import build_slice_manifest
from nbatools.development_data import MANIFEST, DevelopmentSnapshot, sha256
from tools.development_snapshot import _safe_contracts, write_json

E = Path(__file__).resolve().parent
EVIDENCE = E.parent
PARENT = EVIDENCE / "player-period-reader-20261110"
PERIODS = EVIDENCE / "current123-periods-20261107"
BOOK_DIR = PERIODS / "hosted-initial/acquired_data/current123-game184-book"
VERSION = "current123-whole-rebound-development-v7"
SEASON, SEASON_TYPE = "2026-27", "Regular Season"
SUFFIX = "2026-27_regular_season.csv"
DATASET = f"data/raw/player_game_stats/{SUFFIX}"
PARENT_ARCHIVE_SHA = "b2c34ea7603662c191fa0e3dcf8518478563e003ece9f068161eebe0ebae4d7d"
PARENT_MANIFEST_SHA = "e46b6748887d263a342b44dd896e6f4cd2619fd824428f4842dda5be0ac380b7"
PARENT_DATASET_SHA = "334476753a8e3d34e260cdc230c67331a0dac892e8da1e26e1d9edb607bc070d"
BOOK_SHA = "5d11d1974ca1426afda19575cc9a8af316d5a9471f26ced48f8470bbaf830b2b"
ORACLE_SHA = "7d054703091f5f0334d2b01dd7bd978e619d2e36a11eead390fdb23cf0646698"
DQ_ID = "DQ-auto-e148abf704eadc650f2348d031a9c18214073054848a48a6b9d242d84f0ffb1d"
KEY = {"game_id": "0022600184", "team_id": "1610612742", "player_id": "1629023"}
BOX_LINE = (
    "25  P.J. Washington                               F     39:00     7    18     3     8"
    "     4      5     4     6    10    3    2    0   1    1     0      21"
)
# Book columns after MIN: FG FGA 3P 3PA FT FTA OR DR TOT A PF ST TO BS +/- PTS
BOOK_COLUMNS = "fgm fga fg3m fg3a ftm fta oreb dreb reb ast pf stl tov blk plus_minus pts".split()
CHANGES = [("dreb", "5", "6"), ("reb", "9", "10")]
PROCESSED_BUILDER = "build_player_game_features"


def _book_counts():
    pdf = BOOK_DIR / f"{BOOK_SHA}.pdf"
    assert sha256(pdf.read_bytes()) == BOOK_SHA
    capture = json.loads((BOOK_DIR / "capture.json").read_bytes())
    assert capture["sha256"] == BOOK_SHA and capture["game_id"] == KEY["game_id"]
    page = (BOOK_DIR / "page-00.txt").read_text()
    assert "FINAL BOX" in page.splitlines()[0] and "November 4, 2026" in page
    assert "VISITOR: Dallas Mavericks" in page
    lines = [line for line in page.splitlines() if "P.J. Washington" in line]
    assert lines == [BOX_LINE]
    tokens = BOX_LINE.split()
    assert tokens[:5] == ["25", "P.J.", "Washington", "F", "39:00"]
    book = dict(zip(BOOK_COLUMNS, map(int, tokens[5:]), strict=True))
    oracle_raw = (PERIODS / "independent-book-rebound-oracle.json").read_bytes()
    assert sha256(oracle_raw) == ORACLE_SHA
    oracle = json.loads(oracle_raw)
    assert oracle["pdf_sha256"] == BOOK_SHA
    (row,) = [
        r
        for r in oracle["scorer_rows"]
        if r["window"] == "whole" and r["player_id"] == 1629023 and r["team_id"] == 1610612742
    ]
    assert row["raw_line"] == BOX_LINE
    assert (row["oreb"], row["dreb"], row["reb"]) == (book["oreb"], book["dreb"], book["reb"])
    assert (book["oreb"], book["dreb"], book["reb"]) == (4, 6, 10)
    return book


def _rebuild(root, work):
    """Run the existing pure player feature builder in an isolated copy."""
    shutil.copytree(root / "data", work / "data")
    code = (
        f"from nbatools.commands.pipeline.{PROCESSED_BUILDER} import run; "
        "import sys; run(sys.argv[1],sys.argv[2])"
    )
    repo = Path(__file__).resolve().parents[4]
    env = dict(os.environ, PYTHONPATH=str(repo / "src"))
    subprocess.run(
        [sys.executable, "-c", code, SEASON, SEASON_TYPE],
        cwd=work,
        env=env,
        check=True,
        capture_output=True,
    )
    return (work / f"data/processed/player_game_features/{SUFFIX}").read_bytes()


def apply(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    book = _book_counts()
    binding = json.loads((PARENT / "binding.json").read_bytes())
    archive_raw = (PARENT / binding["archive"]).read_bytes()
    assert sha256(archive_raw) == binding["archive_sha256"] == PARENT_ARCHIVE_SHA
    assert binding["manifest_sha256"] == PARENT_MANIFEST_SHA
    root = output / "stage"
    with ZipFile(io.BytesIO(archive_raw)) as z:
        assert all(n.startswith("data/") and ".." not in Path(n).parts for n in z.namelist())
        z.extractall(root)
    prior = DevelopmentSnapshot(root, PARENT_MANIFEST_SHA)
    path = root / DATASET
    before = path.read_bytes()
    # Stale-precondition guard: the base row must still be the observed v4/v5/v6 bytes.
    assert sha256(before) == prior.files[DATASET] == PARENT_DATASET_SHA

    text = before.decode()
    lines = text.splitlines(keepends=True)
    records = list(csv.reader(io.StringIO(text)))
    assert len(records) == len(lines), "Multiline CSV requires the existing full parser"
    header = records[0]
    index = {name: i for i, name in enumerate(header)}
    matches = [
        i
        for i, cells in enumerate(records[1:], 1)
        if all(cells[index[k]].lstrip("0") == v.lstrip("0") for k, v in KEY.items())
    ]
    assert len(matches) == 1
    (row_index,) = matches
    cells = records[row_index]
    # Every other count on the row already equals the official FINAL BOX.
    minutes = float(cells[index["minutes"]])
    assert minutes == 39.0
    for field, value in book.items():
        if field not in {"dreb", "reb"}:
            assert float(cells[index[field]]) == value, field
    ledger = []
    for field, old, new in CHANGES:
        assert cells[index[field]] == old, "Correction conflict or stale old value"
        assert int(new) == book[field]
        cells[index[field]] = new
        ledger.append(
            dict(
                key=KEY,
                field=field,
                before=int(old),
                after=int(new),
                before_token=old,
                after_token=new,
                evidence=dict(
                    reference=str((BOOK_DIR / f"{BOOK_SHA}.pdf").relative_to(EVIDENCE.parents[2])),
                    sha256=BOOK_SHA,
                    zero_based_page=0,
                    page_heading="OFFICIAL SCORER'S REPORT FINAL BOX",
                    literal_line=BOX_LINE,
                    oracle_sha256=ORACLE_SHA,
                ),
            )
        )
    assert int(cells[index["oreb"]]) + int(cells[index["dreb"]]) == int(cells[index["reb"]])
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\n").writerow(cells)
    new_line = buffer.getvalue()
    old_line = lines[row_index]
    assert old_line.endswith("\n") and new_line.count(",") == old_line.count(",")
    lines[row_index] = new_line
    path.write_text("".join(lines))
    after = path.read_bytes()
    # Exactly two cells on one line differ.
    diff = [
        (a, b)
        for a, b in zip(before.decode().splitlines(), after.decode().splitlines(), strict=True)
        if a != b
    ]
    assert len(diff) == 1
    old_cells, new_cells = (next(csv.reader([x])) for x in diff[0])
    changed = [h for h, a, b in zip(header, old_cells, new_cells, strict=True) if a != b]
    assert changed == ["dreb", "reb"]

    # Whole-game invariants that the correction must satisfy season-wide.
    players = pd.read_csv(path)
    teams = pd.read_csv(root / f"data/raw/team_game_stats/{SUFFIX}")
    assert (players.oreb + players.dreb == players.reb).all()
    sums = players.groupby(["game_id", "team_id"])[["oreb", "dreb", "reb"]].sum().reset_index()
    joined = sums.merge(teams, on=["game_id", "team_id"], suffixes=("_players", ""))
    assert len(joined) == len(teams) == 246
    mismatched = joined[
        (joined.oreb_players != joined.oreb)
        | (joined.dreb_players != joined.dreb)
        | (joined.reb_players != joined.reb)
    ]
    assert mismatched.empty, mismatched  # v6 had exactly game184/DAL 31/49 vs 32/50
    periods = pd.read_csv(root / f"data/raw/player_game_period_stats/{SUFFIX}")
    mine = periods[
        periods.game_id.eq(22600184)
        & periods.player_id.eq(1629023)
        & periods.period_family.isin(["quarter", "overtime"])
    ]
    assert (mine.dreb.sum(), mine.reb.sum()) == (6, 10)

    # Derived processed inputs: rebuild with the existing builder before and after.
    # Game184 is this player's last game at the fixed123 cutoff and the feature uses
    # only prior games, so the correct dependent recalculation is no change; the
    # retained v6 processed bytes stay (avoids unrelated float-format churn).
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        stage_before = tmp / "before"
        stage_before.mkdir()
        with ZipFile(io.BytesIO(archive_raw)) as z:
            z.extractall(stage_before)
        rebuilt_before = _rebuild(stage_before, tmp / "rb")
        rebuilt_after = _rebuild(root, tmp / "ra")
    assert rebuilt_before == rebuilt_after
    features = pd.read_csv(root / f"data/processed/player_game_features/{SUFFIX}")
    later = features[features.player_id.eq(1629023) & (features.game_date > "2026-11-04")]
    assert later.empty
    # Team/league/game builders read team_game_stats only (unchanged bytes).

    _safe_contracts(root, SEASON, SEASON_TYPE)
    report = build_slice_manifest(
        SEASON, SEASON_TYPE, data_root=root / "data", generation_id=VERSION
    )
    assert report["validation_state"] == "passed"
    for rel, digest in prior.files.items():
        if rel != DATASET:
            assert sha256((root / rel).read_bytes()) == digest, rel

    correction = dict(
        schema_version=1,
        kind="whole_game_player_count_correction",
        exception_id=DQ_ID,
        base_version=prior.document["version"],
        base_manifest_sha256=PARENT_MANIFEST_SHA,
        base_archive_sha256=PARENT_ARCHIVE_SHA,
        dataset_path=DATASET,
        source_sha256=PARENT_DATASET_SHA,
        corrected_sha256=sha256(after),
        csv_line_number=row_index + 1,
        changes=ledger,
        unchanged_row_counts_verified=sorted(k for k in book if k not in {"dreb", "reb"}),
        season_team_rebound_sums_match=246,
        player_quarter_sum_matches_whole=True,
        processed_rebuild_invariant=[f"data/processed/player_game_features/{SUFFIX}"],
        old484_rate_unknowns_preserved=True,
        source_originals_changed=False,
        new_source_requests=0,
        production_writes=0,
        full_snapshot_accepted=False,
    )
    write_json(root / "data/metadata/corrections/game184-whole-rebound.json", correction)
    report_path = "data/metadata/whole-rebound-validation.json"
    report_sha = write_json(root / report_path, report)
    doc = dict(
        prior.document,
        version=VERSION,
        scope=(
            "v6 plus scorer-qualified whole-game game184/PID1629023 DREB6/REB10; "
            "old484unknowns/DQ006/freshness/publication remain open"
        ),
        validation_reports=[
            *prior.document["validation_reports"],
            dict(
                kind="whole_game_player_counts",
                dataset_path=DATASET,
                path=report_path,
                sha256=report_sha,
                state="passed",
            ),
        ],
    )
    doc["files"] = {
        p.relative_to(root).as_posix(): sha256(p.read_bytes())
        for p in sorted((root / "data").rglob("*"))
        if p.is_file() and p.relative_to(root) != MANIFEST
    }
    assert set(doc["files"]) == set(prior.files) | {
        "data/metadata/corrections/game184-whole-rebound.json",
        report_path,
    }
    digest = write_json(root / MANIFEST, doc)
    DevelopmentSnapshot(root, digest)
    archive = output / "current123-whole-rebound-v7.zip"
    with ZipFile(archive, "x", ZIP_DEFLATED) as z:
        for p in sorted((root / "data").rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(root).as_posix())
    result = dict(
        archive=archive.name,
        archive_sha256=sha256(archive.read_bytes()),
        manifest_sha256=digest,
        parent_manifest_sha256=PARENT_MANIFEST_SHA,
        parent_archive_sha256=PARENT_ARCHIVE_SHA,
        exception_id=DQ_ID,
        changed_cells=2,
        source_originals_changed=False,
        new_source_requests=0,
        production_writes=0,
    )
    write_json(output / "binding.json", result)
    write_json(output / "correction.json", correction)
    return result


if __name__ == "__main__":
    print(json.dumps(apply(Path(sys.argv[1])), indent=2))
