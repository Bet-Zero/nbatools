"""Exact-base, append-only availability overlays; no network or publication calls."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re

_PATH = re.compile(
    r"raw/player_game_availability/(?:19|20)\d{2}-\d{2}_(?:regular_season|playoffs)\.(csv|imports\.json)"
)
_KEYS = ("game_id", "team_id", "player_id")


def binding(before: bytes, game_ids: list[str], *, added_records: int) -> dict:
    return dict(
        base_sha256=hashlib.sha256(before).hexdigest(),
        base_size_bytes=len(before),
        added_game_ids=game_ids,
        added_records=added_records,
    )


def _scope(relative: str, before: bytes, spec: dict) -> tuple[str, set[int]]:
    match = _PATH.fullmatch(relative)
    if not match or set(spec) != {
        "base_sha256",
        "base_size_bytes",
        "added_game_ids",
        "added_records",
    }:
        raise ValueError("Append binding is not a reviewed availability path/schema")
    if (
        len(before) != spec["base_size_bytes"]
        or hashlib.sha256(before).hexdigest() != spec["base_sha256"]
    ):
        raise ValueError("Append base bytes differ from the reviewed binding")
    games = spec["added_game_ids"]
    if (
        not isinstance(games, list)
        or not games
        or any(
            not isinstance(g, str) or not re.fullmatch(r"[0-9]{10}", g) or int(g) <= 0
            for g in games
        )
    ):
        raise ValueError("Append requires explicit positive ten-digit game IDs")
    if len(set(games)) != len(games):
        raise ValueError("Duplicate append game IDs")
    if type(spec["added_records"]) is not int or spec["added_records"] <= 0:
        raise ValueError("Invalid reviewed append record count")
    return match.group(1), {int(g) for g in games}


def _table(raw: bytes) -> tuple[list[str], list[dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))
    header = reader.fieldnames
    rows = list(reader)
    if (
        not header
        or len(set(header)) != len(header)
        or not set(_KEYS) <= set(header)
        or not rows
        or any(None in row or None in row.values() for row in rows)
    ):
        raise ValueError("Invalid availability append table")
    return header, rows


def _key(row: dict[str, str]) -> tuple[int, int, int]:
    try:
        values = tuple(int(row[k]) for k in _KEYS)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid availability append identity") from exc
    if any(v <= 0 for v in values):
        raise ValueError("Invalid availability append identity")
    return values


def _indexed(rows: list[dict[str, str]]) -> dict[tuple[int, int, int], dict[str, str]]:
    result = {_key(row): row for row in rows}
    if len(result) != len(rows):
        raise ValueError("Duplicate availability append identity")
    # One player cannot appear on both sides of the same game.
    if len({(g, p) for g, _, p in result}) != len(result):
        raise ValueError("Conflicting availability append sides")
    return result


def _unique_object(pairs):
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("Duplicate import-lineage key")
    return dict(pairs)


def verify_append(relative: str, before: bytes, after: bytes, spec: dict) -> None:
    """Permit only exact old facts plus the registered new game populations.

    This is an additional preservation gate, never source qualification. The
    existing complete-snapshot validator must still rebuild/qualify every row.
    """
    kind, games = _scope(relative, before, spec)
    if kind == "csv":
        old_header, old_rows = _table(before)
        new_header, new_rows = _table(after)
        if old_header != new_header:
            raise ValueError("Availability append schema changed")
        old, new = _indexed(old_rows), _indexed(new_rows)
        if any(new.get(key) != row for key, row in old.items()):
            raise ValueError("Availability append changed or removed an existing cell/row")
        if len(new) - len(old) != spec["added_records"]:
            raise ValueError("Availability append row count differs")
        if games & {key[0] for key in old} or {key[0] for key in new.keys() - old.keys()} != games:
            raise ValueError("Availability append changed the reviewed new-game scope")
    else:
        old = json.loads(before, object_pairs_hook=_unique_object)
        new = json.loads(after, object_pairs_hook=_unique_object)
        if not isinstance(old, dict) or not old or not isinstance(new, dict):
            raise ValueError("Invalid availability import lineage")
        if any(new.get(key) != value for key, value in old.items()):
            raise ValueError("Availability append changed or removed existing import lineage")
        if len(new) - len(old) != spec["added_records"]:
            raise ValueError("Availability import-lineage count differs")
        expected = {str(g) for g in games}
        if expected & old.keys() or new.keys() - old.keys() != expected:
            raise ValueError("Availability import-lineage append scope changed")


def preserve_cells(relative: str, before: bytes, normalized: bytes, spec: dict) -> bytes:
    """Restore original serialized cells after the existing pandas producer.

    Old report clocks/source authority must survive float/dtype round trips.
    New facts still come exclusively from the qualified producer output.
    """
    kind, _ = _scope(relative, before, spec)
    if kind != "csv":
        raise ValueError("Cell preservation is only for availability CSVs")
    old_header, old_rows = _table(before)
    header, rows = _table(normalized)
    if old_header != header:
        raise ValueError("Availability append schema changed")
    old, new = _indexed(old_rows), _indexed(rows)
    if not old.keys() <= new.keys():
        raise ValueError("Producer dropped existing availability rows")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    writer.writerows(old.get(_key(row), row) for row in rows)
    raw = output.getvalue().encode("utf-8")
    verify_append(relative, before, raw, spec)
    return raw
