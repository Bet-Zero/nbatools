"""Source-reported absence reasons, separate from binary participation and health."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter

import pandas as pd

from nbatools.commands import _participation_observations as participation
from nbatools.commands._player_identity import player_name_mask
from nbatools.data_source import (
    data_exists,
    data_generation_context,
    data_path,
    data_source_cache_key,
)
from nbatools.dataframe_cache import FRAME_CACHE

DIRECTORY = "raw/player_game_absence_reasons/"
SOURCES = "raw/player_game_absence_reason_sources/"
COLUMNS = (
    "game_id",
    "game_date",
    "season",
    "season_type",
    "team_id",
    "player_id",
    "player_name",
    "reported_reason",
    "reason_text",
    "source_kind",
    "source_url",
    "source_sha256",
    "source_locator",
    "identity_source_sha256",
    "coverage_scope",
)
SCOPE = "listed_player_reported_reason_only"
BASIS = "officially reported Rest"


class ReasonCoverageError(ValueError):
    """A requested reported reason cannot be qualified over the selected population."""


def classify_reason(text: str) -> str:
    """Classify a qualified source field, never an arbitrary availability comment."""
    value = re.sub(
        r"^(?:INACTIVE|DNP|DND|NWT|DID NOT PLAY|DID NOT DRESS)\s*-\s*", "", text.strip(), flags=re.I
    )
    value = " ".join(value.split()).casefold()
    if value == "rest":
        return "reported_rest"
    if (
        not value
        or value
        in {
            "inactive",
            "dnp",
            "dnd",
            "nwt",
            "did not play",
            "did not dress",
            "unknown",
            "n/a",
            "none",
            "-",
            "unspecified",
            "not reported",
            "tbd",
        }
        or "explicit listed row" in value
        or re.search(r"\brest(?:ed|ing)?\b", value)
    ):
        return "unknown"
    return "reported_other"


def key(row):
    return ":".join(str(int(row[field])) for field in ("game_id", "team_id", "player_id"))


def row_digest(row):
    payload = {field: str(row[field]) for field in COLUMNS}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def validate_rows(frame, ledger, *, source_entry):
    if set(frame.columns) != set(COLUMNS) or frame.empty:
        raise ValueError("Incomplete reported-reason observation schema")
    for col in ("game_id", "team_id", "player_id"):
        participation._ids(frame[col])
    if frame.duplicated(["game_id", "player_id"]).any():
        raise ValueError("Duplicate or conflicting reported-reason identity")
    if (
        not frame.coverage_scope.eq(SCOPE).all()
        or not frame.reported_reason.isin(["reported_rest", "reported_other", "unknown"]).all()
    ):
        raise ValueError("Invalid reported-reason observation scope/state")
    if set(ledger) != {key(row) for row in frame.to_dict("records")}:
        raise ValueError("Reported-reason lineage does not match observations")
    for row in frame.to_dict("records"):
        record = ledger[key(row)]
        if (
            record["row_sha256"] != row_digest(row)
            or classify_reason(row["reason_text"]) != row["reported_reason"]
        ):
            raise ValueError("Reported-reason row differs from qualified lineage")
        for field in ("source_sha256", "identity_source_sha256"):
            if re.fullmatch(r"[a-f0-9]{64}", row[field]) is None:
                raise ValueError("Invalid reported-reason source digest")
        if row["source_kind"] not in {"nba_official_finalbox", "nba_stats_structured_archive"}:
            raise ValueError("Unqualified reported-reason source kind")
        for field in ("source_file", "source_receipt"):
            item = record[field]
            if (
                not item["path"].startswith(SOURCES)
                or "/" in item["path"][len(SOURCES) :]
                or ".." in item["path"]
            ):
                raise ValueError("Invalid reported-reason retained source path")
            if source_entry(item["path"]) != item:
                raise ValueError("Reported-reason source binding differs from immutable manifest")
        if record["source_file"]["sha256"] != row["source_sha256"]:
            raise ValueError("Reported-reason original source digest mismatch")


def load_observations(seasons, season_type):
    def load():
        frames = []
        with data_generation_context() as generation:
            manifest = None
            for season in seasons:
                suffix = f"{season}_{season_type.lower().replace(' ', '_')}.csv"
                relative = DIRECTORY + suffix
                ledger_path = relative.removesuffix(".csv") + ".imports.json"
                if not data_exists("data/" + relative) and not data_exists("data/" + ledger_path):
                    continue
                if manifest is None:
                    manifest = json.loads(
                        data_path("data/metadata/generation_manifest.json").read_bytes()
                    )
                    if manifest["generation_id"] != generation:
                        raise ValueError("Reported-reason manifest generation differs")
                    entries = {r["path"]: r for r in manifest["files"]}
                    if len(entries) != len(manifest["files"]):
                        raise ValueError("Duplicate reported-reason manifest paths")

                def verified(path):
                    if path not in entries:
                        raise ValueError("Unmanifested reported-reason dependency")
                    item = entries[path]
                    raw = data_path("data/" + path).read_bytes()
                    if (
                        len(raw) != item["size_bytes"]
                        or hashlib.sha256(raw).hexdigest() != item["sha256"]
                    ):
                        raise ValueError("Reported-reason bytes differ from immutable manifest")
                    return raw

                import io

                frame = pd.read_csv(
                    io.BytesIO(verified(relative)), dtype=str, keep_default_na=False
                )
                ledger = json.loads(verified(ledger_path))
                validate_rows(frame, ledger, source_entry=entries.__getitem__)
                if not (frame.season.eq(season) & frame.season_type.eq(season_type)).all():
                    raise ValueError("Reported-reason season/type mismatch")
                # Bind each reason to the existing qualified DNP and its unchanged import digest.
                availability_path = "raw/player_game_availability/" + suffix
                binary = pd.read_csv(
                    io.BytesIO(verified(availability_path)), dtype=str, keep_default_na=False
                )
                imports = json.loads(
                    verified(availability_path.removesuffix(".csv") + ".imports.json")
                )
                validate_identity_bindings(frame, ledger, binary, imports)
                for col in ("game_id", "team_id", "player_id"):
                    frame[col] = participation._ids(frame[col])
                frames.append(frame)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLUMNS)

    return FRAME_CACHE.get_or_load(
        ("reported_absence_reasons", data_source_cache_key(), tuple(seasons), season_type), load
    )


def validate_identity_bindings(frame, ledger, binary, imports):
    from nbatools.commands.pipeline.pull_player_game_availability import _game_digest

    for row in frame.to_dict("records"):
        group = binary.loc[pd.to_numeric(binary.game_id).eq(int(row["game_id"]))]
        observed = group.loc[
            pd.to_numeric(group.team_id).eq(int(row["team_id"]))
            & pd.to_numeric(group.player_id).eq(int(row["player_id"]))
        ]
        record = ledger[key(row)]
        if (
            len(observed) != 1
            or observed.participation_state.item() != "did_not_play"
            or observed.game_date.item() != row["game_date"]
            or observed.source_sha256.item() != row["identity_source_sha256"]
            or not player_name_mask(observed, row["player_name"]).all()
        ):
            raise ValueError("Reported reason lacks qualified same-game DNP identity")
        imported = imports[str(int(row["game_id"]))]
        if imported != record["identity_import"] or imported["sha256"] != _game_digest(group):
            raise ValueError("Reported-reason DNP import lineage changed")


def filter_reported_rest(
    candidates, name, seasons, season_type, *, opponent_context=False, evidence=None
):
    if " and " in name.casefold():
        raise ValueError("Reported-rest conditions require one scalar absent player")
    scope = ["game_id", "team_id", "game_date"]
    if opponent_context:
        scope.append("opponent_team_id")
    population = candidates.drop_duplicates(scope)
    evidence = {} if evidence is None else evidence
    evidence.update(
        basis=BASIS,
        complete=False,
        requested_games=len(population),
        qualified_nonparticipations=0,
        reported_rest=0,
        reported_other=0,
        unknown=0,
    )
    try:
        absent = participation.filter_absent(
            population, name, seasons, season_type, opponent_context=opponent_context
        )
        observations = load_observations(seasons, season_type)
    except (ValueError, FileNotFoundError, KeyError) as exc:
        raise ReasonCoverageError(f"Reported-rest source qualification failed: {exc}") from exc
    evidence["qualified_nonparticipations"] = len(absent)
    matching = observations.loc[player_name_mask(observations, name)]
    keep, counts = [], Counter()
    for row in absent.itertuples():
        sides = [int(row.team_id)]
        if opponent_context:
            sides.append(int(row.opponent_team_id))
        facts = matching.loc[matching.game_id.eq(int(row.game_id)) & matching.team_id.isin(sides)]
        if (
            len(facts) != 1
            or pd.Timestamp(facts.game_date.item()).date() != pd.Timestamp(row.game_date).date()
        ):
            counts["unknown"] += 1
            continue
        state = facts.reported_reason.item()
        counts[state] += 1
        if state == "reported_rest":
            keep.append((int(row.game_id), int(row.team_id)))
    evidence.update(
        {state: counts[state] for state in ("reported_rest", "reported_other", "unknown")}
    )
    if counts["unknown"]:
        raise ReasonCoverageError(f"Incomplete officially reported Rest reason coverage for {name}")
    evidence["complete"] = True
    rest_keys = set(keep)
    result = candidates.loc[
        [(int(g), int(t)) in rest_keys for g, t in zip(candidates.game_id, candidates.team_id)]
    ].copy()
    result.attrs["reported_reason_coverage"] = evidence.copy()
    return result


def coverage_note(coverage):
    if not coverage.get("complete"):
        return (
            "Officially reported Rest coverage is incomplete; no Rest total is established. "
            f"Unknown selected nonparticipations: {coverage.get('unknown', 'unavailable')}."
        )
    return (
        f"Officially reported Rest: {coverage.get('reported_rest', 0)} Rest, "
        f"{coverage.get('reported_other', 0)} reported other, "
        f"{coverage.get('unknown', 0)} unknown among "
        f"{coverage.get('qualified_nonparticipations', 0)} qualified nonparticipations "
        f"in {coverage.get('requested_games', 0)} selected games. "
        "Reported reasons do not establish clinical or healthy status."
    )
