"""One pinned read-only audit of direct retained K08 participation dependencies."""

import hashlib
import io
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import data_exists, data_path
from tools.participation_coverage import build_report

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
GENERATION = "availability-lebron-season-v1-20261031"
MANIFEST = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
SCOPES = [("2023-24", 1610612747, [203076, 2544, 1630559])]
OLD_TATUM = (
    Path(__file__).resolve().parents[1]
    / "working/nba-tools-completion-program/source-evidence/k08-coverage/selected-populations.json"
)
AVAILABILITY_COLUMNS = [
    "game_id",
    "game_date",
    "team_id",
    "player_id",
    "player_name",
    "participation_state",
]


def _raw_population(catalog, teams, season, team_id):
    own = teams.loc[pd.to_numeric(teams.team_id, errors="raise").eq(team_id)].copy()
    assert len(own) == own.game_id.nunique() == 82
    assert own.season.eq(season).all() and own.season_type.eq("Regular Season").all()
    assert not catalog.game_id.duplicated().any()
    for game in own.itertuples():
        rows = teams.loc[teams.game_id.eq(game.game_id)]
        assert len(rows) == rows.team_id.nunique() == 2
        assert set(rows.team_id) == set(rows.opponent_team_id)
        assert set(rows.team_id) == {team_id, int(game.opponent_team_id)}
        assert rows.season.eq(season).all() and rows.season_type.eq("Regular Season").all()
        row = catalog.loc[catalog.game_id.eq(game.game_id)]
        assert len(row) == 1 and str(row.is_final.item()).lower() in {"true", "1"}
        assert row.season.item() == season and row.season_type.item() == "Regular Season"
        day = pd.Timestamp(row.game_date.item()).date()
        assert pd.to_datetime(rows.game_date).dt.date.eq(day).all()
        known_sides = [
            int(row[field].item())
            for field in ("home_team_id", "away_team_id")
            if field in row and pd.notna(row[field].item())
        ]
        assert len(known_sides) == len(set(known_sides))
        assert set(known_sides) <= set(rows.team_id)
    return own


def _raw_states(teams, players, availability, team_id, people):
    dates = {int(r.game_id): pd.Timestamp(r.game_date).date() for r in teams.itertuples()}
    opponents = {int(r.game_id): int(r.opponent_team_id) for r in teams.itertuples()}
    facts = defaultdict(lambda: defaultdict(set))
    invalid = set()
    for frame, appearance in ((players, True), (availability, False)):
        selected = frame.loc[pd.to_numeric(frame.player_id).isin(people)].copy()
        if appearance:
            selected = selected.loc[pd.to_numeric(selected.minutes, errors="coerce").gt(0)]
        selected = selected.loc[pd.to_numeric(selected.game_id).isin(dates)]
        for key, count in selected.groupby(["game_id", "player_id"]).size().items():
            if count != 1:
                invalid.add(tuple(map(int, key)))
        for row in selected.itertuples():
            gid, pid, tid = int(row.game_id), int(row.player_id), int(row.team_id)
            key = gid, pid
            if pd.Timestamp(row.game_date).date() != dates[gid] or tid not in {
                team_id,
                opponents[gid],
            }:
                invalid.add(key)
            state = "played" if appearance else row.participation_state
            facts[key][tid].add(state)
    result = {}
    for pid in people:
        result[pid] = {}
        for gid in dates:
            key, state = (gid, pid), "unknown"
            sides = facts[(gid, pid)]
            if key not in invalid and len(sides) == 1:
                tid, values = next(iter(sides.items()))
                if len(values) == 1 and values <= {"played", "did_not_play", "unknown"}:
                    if tid == team_id:
                        state = next(iter(values))
                    else:
                        state = "same_game_other_side"
            result[pid][gid] = state
    return result


def test_current_direct_lal_2023_dependencies_and_optional_tatum_2024_audit():
    assert os.environ["NBATOOLS_DATA_GENERATION"] == GENERATION
    manifest_raw = data_path("data/metadata/generation_manifest.json").read_bytes()
    assert hashlib.sha256(manifest_raw).hexdigest() == MANIFEST
    manifest = json.loads(manifest_raw)
    assert manifest["generation_id"] == GENERATION
    entries = {row["path"]: row for row in manifest["files"]}
    assert len(entries) == len(manifest["files"])
    checked, absent = {}, []

    def verified(relative, optional=False):
        if relative not in entries:
            assert optional, relative
            assert not data_exists("data/" + relative), "Unmanifested configured source file"
            absent.append(relative)
            return None
        raw = data_path("data/" + relative).read_bytes()
        item = entries[relative]
        assert len(raw) == item["size_bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"]
        checked[relative] = item
        return raw

    verified("metadata/player_names.csv")
    old = json.loads(OLD_TATUM.read_bytes())
    old_scope = next(row for row in old["populations"] if row["season"] == "2024-25")
    old_unknown = sorted(
        int(row["game_id"]) for row in old_scope["games"] if row["state"] == "unknown"
    )
    old_hashes = old["source_hashes"]
    # The historical proof binds team/player tables, but not the finalized
    # catalog, published identity or availability presence used by today's
    # report. It cannot establish all current exact keys merely from two hashes.
    required_old_bindings = {
        "metadata/player_names.csv",
        *(
            f"raw/{kind}/2024-25_regular_season.csv"
            for kind in ("games", "team_game_stats", "player_game_stats")
        ),
    }
    for kind in ("player_game_availability", "player_season_advanced"):
        relative = f"raw/{kind}/2024-25_regular_season.csv"
        if relative in entries:
            required_old_bindings.add(relative)
    missing_old_bindings = sorted(required_old_bindings - set(old_hashes))
    changed_old_bindings = sorted(
        path
        for path in required_old_bindings & set(old_hashes)
        if entries.get(path, {}).get("sha256") != old_hashes[path]
    )
    unbound_optional_absences = sorted(
        f"raw/{kind}/2024-25_regular_season.csv"
        for kind in ("player_game_availability", "player_season_advanced")
        if f"raw/{kind}/2024-25_regular_season.csv" not in entries
        and f"raw/{kind}/2024-25_regular_season.csv"
        not in old.get("manifest_absent_optional_paths", [])
    )
    can_reuse = not (missing_old_bindings or changed_old_bindings or unbound_optional_absences)
    scopes = list(SCOPES)
    if not can_reuse:
        scopes.append(("2024-25", 1610612738, [1628369]))
    assert sum(len(people) for _, _, people in scopes) <= 4
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "direct-k08-participation-coverage"
    output.mkdir(parents=True, exist_ok=False)
    reports = []
    for season, team_id, people in scopes:
        suffix = season + "_regular_season.csv"
        frames = {
            kind: pd.read_csv(io.BytesIO(verified(f"raw/{kind}/" + suffix)))
            for kind in ("games", "team_game_stats", "player_game_stats")
        }
        availability_raw = verified("raw/player_game_availability/" + suffix, optional=True)
        availability = (
            pd.read_csv(io.BytesIO(availability_raw))
            if availability_raw is not None
            else pd.DataFrame(columns=AVAILABILITY_COLUMNS)
        )
        verified("raw/player_season_advanced/" + suffix, optional=True)
        teams = _raw_population(frames["games"], frames["team_game_stats"], season, team_id)
        players = (
            frames["player_game_stats"]
            .loc[frames["player_game_stats"].player_id.isin(people)]
            .copy()
        )
        listed = availability.loc[availability.player_id.isin(people)].copy()
        expected = _raw_states(teams, players, listed, team_id, people)
        prefix = f"{season}-{team_id}"
        catalog = frames["games"].loc[frames["games"].game_id.isin(teams.game_id)]
        for name, rows in (
            ("team82", teams),
            (
                "reciprocal-team164",
                frames["team_game_stats"].loc[
                    frames["team_game_stats"].game_id.isin(teams.game_id)
                ],
            ),
            ("catalog82", catalog),
            ("target-player-rows", players),
            ("target-ledger-rows", listed),
        ):
            rows.to_csv(output / f"{prefix}-{name}.csv", index=False)
        for pid in people:
            report = build_report(
                generation=GENERATION,
                manifest_sha256=MANIFEST,
                season=season,
                team_id=team_id,
                player_id=pid,
            )
            assert report["observed_team_games"] == report["requested_games"] == 82
            assert report["counts"] == {
                state: Counter(expected[pid].values())[state]
                for state in ("played", "did_not_play", "same_game_other_side", "unknown")
            }
            assert {int(row["game_id"]): row["state"] for row in report["games"]} == expected[pid]
            dates = {
                int(row.game_id): pd.Timestamp(row.game_date).strftime("%Y-%m-%d")
                for row in teams.itertuples()
            }
            assert all(
                row["game_date"] == dates[int(row["game_id"])]
                and row["team_id"] == team_id
                and row["player_id"] == pid
                for row in report["games"]
            )
            assert sorted(report["missing_keys"], key=lambda row: row["game_id"]) == [
                dict(game_id=f"{gid:010d}", game_date=dates[gid], team_id=team_id, player_id=pid)
                for gid, state in sorted(expected[pid].items())
                if state == "unknown"
            ]
            if report["missing_keys"]:
                assert (
                    report["missed_games"] is None and not report["complete_requested_population"]
                )
            else:
                assert report["complete_requested_population"]
                assert report["missed_games"] == report["counts"]["did_not_play"]
            assert all(
                path in checked and checked[path]["sha256"] == digest
                for path, digest in report["source_hashes"].items()
            )
            (output / f"{season}-{pid}-coverage.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
            reports.append(report)
    receipt = dict(
        classification="read_only_current_input_audit_not_DNP_inference_collection_or_publication",
        generation=GENERATION,
        manifest_sha256=MANIFEST,
        scopes=[dict(season=s, team_id=t, player_ids=p) for s, t, p in scopes],
        source_files=sorted(checked.values(), key=lambda r: r["path"]),
        manifest_absent_optional_paths=sorted(set(absent)),
        absence_table_policy="Manifest-absent availability is an empty evidence table; missing rows stay unknown unless positive/exact-game association qualifies them.",
        historical_tatum_proof=dict(
            path=OLD_TATUM.relative_to(Path(__file__).resolve().parents[1]).as_posix(),
            sha256=hashlib.sha256(OLD_TATUM.read_bytes()).hexdigest(),
            old_generation=old["generation"],
            old_source_hashes=old_hashes,
            old_unknown_ids=old_unknown,
            reuse_as_current_proof=can_reuse,
            missing_current_dependency_bindings=missing_old_bindings,
            changed_input_hashes=changed_old_bindings,
            unbound_optional_absences=unbound_optional_absences,
            action="Reused only as historical corroboration; one current fourth scope audited"
            if not can_reuse
            else "Reused current-bound old exact keys",
        ),
        subset_sha256={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob("*.csv")
        },
        missing_keys=[key for report in reports for key in report["missing_keys"]],
        collection_requirement="Inspect qualification errors and reuse accepted evidence before proposing only exact unresolved keys; unknown is not DNP.",
        production_writes=0,
        nba_source_requests=0,
    )
    (output / "source-bindings.json").write_text(json.dumps(receipt, indent=2) + "\n")
