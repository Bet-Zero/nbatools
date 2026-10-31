"""Synthetic preservation gates; fixture bytes are never NBA evidence."""

import csv
import io
import json

import pytest

from tools.availability_overlay import binding, preserve_cells, verify_append

pytestmark = pytest.mark.engine
CSV = "raw/player_game_availability/2025-26_regular_season.csv"
LEDGER = CSV.removesuffix(".csv") + ".imports.json"
FIELDS = ["game_id", "team_id", "player_id", "source_minutes", "source", "source_comment"]
OLD = dict(
    game_id="0022500002",
    team_id="1",
    player_id="11",
    source_minutes="21.299999999999997",
    source="qualified_pdf",
    source_comment="",
)
NEW = [
    dict(OLD, game_id="0022500019", player_id="12"),
    dict(OLD, game_id="0022500113", player_id="13"),
]
GAMES = [row["game_id"] for row in NEW]


def table(rows, fields=FIELDS):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


def test_append_retains_every_original_cell_and_game_identity():
    before, after = table([OLD]), table([OLD, *NEW])
    verify_append(CSV, before, after, binding(before, GAMES, added_records=2))
    normalized = table([dict(OLD, source_minutes="21.3"), *NEW])
    preserved = preserve_cells(CSV, before, normalized, binding(before, GAMES, added_records=2))
    rows = list(csv.DictReader(io.StringIO(preserved.decode())))
    assert rows[0] == OLD
    assert rows[1:] == NEW


@pytest.mark.parametrize(
    "damage",
    [
        "changed_cell",
        "removed_old",
        "duplicate",
        "changed_side",
        "extra_game",
        "missing_game",
        "changed_schema",
        "wrong_base",
        "wrong_count",
    ],
)
def test_unreviewed_csv_mutation_is_rejected(damage):
    before, rows = table([OLD]), [OLD.copy(), *[r.copy() for r in NEW]]
    spec = binding(before, GAMES, added_records=2)
    fields = FIELDS
    if damage == "changed_cell":
        rows[0]["source_minutes"] = "21.3"
    elif damage == "removed_old":
        rows = rows[1:]
    elif damage == "duplicate":
        rows.append(rows[-1].copy())
    elif damage == "changed_side":
        rows[0]["team_id"] = "2"
    elif damage == "extra_game":
        rows[-1]["game_id"] = "0022500122"
    elif damage == "missing_game":
        rows = rows[:-1]
    elif damage == "changed_schema":
        fields = FIELDS[::-1]
    elif damage == "wrong_base":
        spec["base_sha256"] = "0" * 64
    else:
        spec["added_records"] = 3
    with pytest.raises(ValueError):
        verify_append(CSV, before, table(rows, fields), spec)


def test_exact_ledger_extension_preserves_nested_old_receipt():
    old = {"22500002": {"source": "report", "sha256": "a" * 64}}
    new = old | {str(int(g)): {"source": "report", "sha256": "b" * 64} for g in GAMES}
    before = json.dumps(old).encode()
    verify_append(LEDGER, before, json.dumps(new).encode(), binding(before, GAMES, added_records=2))


@pytest.mark.parametrize(
    "damage", ["changed", "removed", "duplicate_key", "alias_key", "wrong_count", "wrong_game"]
)
def test_lineage_cannot_rewrite_or_smuggle_games(damage):
    before = b'{"22500002":{"source":"report","sha256":"old"}}'
    new = json.loads(before) | {"22500019": {"source": "report"}, "22500113": {"source": "report"}}
    spec = binding(before, GAMES, added_records=2)
    if damage == "changed":
        new["22500002"]["sha256"] = "changed"
    elif damage == "removed":
        del new["22500002"]
    elif damage == "alias_key":
        new["0022500019"] = new.pop("22500019")
    elif damage == "wrong_count":
        spec["added_records"] = 3
    elif damage == "wrong_game":
        new["22500122"] = new.pop("22500113")
    raw = json.dumps(new).encode()
    if damage == "duplicate_key":
        raw = raw[:-1] + b',"22500002":{"source":"report","sha256":"old"}}'
    with pytest.raises(ValueError):
        verify_append(LEDGER, before, raw, spec)


def test_append_cannot_target_other_datasets_or_expand_metadata():
    before, after = table([OLD]), table([OLD, *NEW])
    spec = binding(before, GAMES, added_records=2)
    for path, policy in [
        ("raw/games/2025-26_regular_season.csv", spec),
        (CSV, spec | {"force": True}),
    ]:
        with pytest.raises(ValueError):
            verify_append(path, before, after, policy)
