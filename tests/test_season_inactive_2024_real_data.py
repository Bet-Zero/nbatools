"""One bounded next-season batch, qualified without publication or acquisition."""

import hashlib
import io
import json
import os
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import pytest

from nbatools.commands._participation_observations import combined_observations
from nbatools.commands.pipeline.pull_player_game_availability import validate_publication
from nbatools.commands.pipeline.structured_participation import (
    inactive_dependencies,
    qualify_season_inactive,
    stage_season_inactive,
)
from nbatools.data_source import data_generation_context, data_path, reset_data_source_cache
from nbatools.dataframe_cache import clear_frame_cache
from nbatools.query_service import execute_natural_query
from tests.test_season_inactive_pilot_real_data import _census

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
PROGRAM = Path(__file__).resolve().parents[1] / "working/nba-tools-completion-program"
EVIDENCE = PROGRAM / "source-evidence/season-inactive-2024"
GENERATION = "availability-season-inactive-2023-v1-20261115"
MANIFEST = "8ec80812ae9dda9222d9d157c253d7a919af214ae40c49a27c20f87b52d156c8"
SEASON = "2024-25"
AVAILABILITY = f"raw/player_game_availability/{SEASON}_regular_season.csv"


def test_next_season_batch_adds_complete_answers_without_inventing_membership(
    tmp_path, monkeypatch, capfd
):
    with data_generation_context() as generation:
        assert generation == GENERATION
        manifest = data_path("data/metadata/generation_manifest.json").read_bytes()
        assert hashlib.sha256(manifest).hexdigest() == MANIFEST
        entries = {e["path"]: e for e in json.loads(manifest)["files"]}
        assert not any(p.startswith("raw/player_team_membership/") for p in entries)
        paths = {
            *inactive_dependencies(SEASON),
            AVAILABILITY,
            f"raw/rosters/{SEASON}.csv",
            "metadata/player_names.csv",
            *(p for p in entries if p.startswith("raw/player_game_availability_sources/")),
        }
        root = tmp_path / "stage/data"
        original = {}
        for path in sorted(paths):
            body = data_path("data/" + path).read_bytes()
            assert hashlib.sha256(body).hexdigest() == entries[path]["sha256"]
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            original[path] = body
        # Replay today's 2023 source with unchanged strict defaults and bytes.
        prefix = "raw/player_game_inactive/2023-24_regular_season"
        old_receipt = json.loads(data_path("data/" + prefix + ".source.json").read_bytes())
        assert "identity_name_policy" not in old_receipt
        old_raw = data_path(
            f"data/raw/player_game_inactive_sources/{old_receipt['sha256']}.csv"
        ).read_bytes()
        old_rows = qualify_season_inactive(
            old_raw,
            old_receipt,
            "2023-24",
            {p: data_path("data/" + p).read_bytes() for p in inactive_dependencies("2023-24")},
        )
        assert (
            old_rows.to_csv(index=False).encode()
            == data_path("data/" + prefix + ".csv").read_bytes()
        )
        assert len(old_rows) == 11010
    stats = pd.read_csv(io.BytesIO(original[inactive_dependencies(SEASON)[-1]]))
    teams = pd.read_csv(io.BytesIO(original[inactive_dependencies(SEASON)[1]]))
    old = pd.read_csv(io.BytesIO(original[AVAILABILITY]))
    roster = pd.read_csv(io.BytesIO(original[f"raw/rosters/{SEASON}.csv"]))
    assert len(teams) == 2460 and teams.groupby("team_id").size().eq(82).all()
    assert len(old) == 347 and old.game_id.nunique() == 10
    with ZipFile(EVIDENCE / "original.zip") as archive:
        raw = archive.read("game_rosters_2025.csv")
    receipt = json.loads((EVIDENCE / "source.json").read_bytes())
    source = pd.read_csv(io.BytesIO(raw))
    source = source.loc[source.season_type_id.eq(2)].copy()
    source["player_name"] = source.first_name + " " + source.last_name
    pairs = {
        (int(t), int(p))
        for frame in (stats, old, roster, source)
        for t, p in zip(frame.team_id, frame.player_id)
    }
    # This retained bulk history expands candidate identities only, never tenure.
    with ZipFile(PROGRAM / "source-evidence/team-membership-20261114/originals.zip") as archive:
        movements = json.loads(archive.read("player-movement.json"))["NBA_Player_Movement"]["rows"]
    for move in movements:
        if "2024-10-21" <= move["TRANSACTION_DATE"][:10] <= "2025-04-13" and move["PLAYER_ID"]:
            pairs.add((int(move["TEAM_ID"]), int(move["PLAYER_ID"])))
            if move["Transaction_Type"] == "Trade":
                pairs.add((int(move["Additional_Sort"]), int(move["PLAYER_ID"])))
    assert len(pairs) == 707
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.parent))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    clear_frame_cache()
    try:
        before, _ = combined_observations([SEASON], "Regular Season")
        baseline, before_full = _census(before, teams, pairs, set(old.game_id))
        inactive = stage_season_inactive(root, raw, receipt, SEASON)
        rejections = inactive.attrs["identity_name_rejections"]
        assert len(source) == 10854 and len(inactive) == 10847 and len(rejections) == 7
        assert all((root / p).read_bytes() == b for p, b in original.items())
        validate_publication(root)
        clear_frame_cache()
        after, _ = combined_observations([SEASON], "Regular Season")
        census, full = _census(after, teams, pairs, set(source.game_id))
        assert baseline["complete_cases"] == 11 and census["complete_cases"] == 69
        assert set(before_full) <= set(full)
        assert len({t for t, p in full}) == 23
        assert not any(
            all((t, p) in full for t, p in pairs if t == tid) for tid in teams.team_id.unique()
        )
        # Independent oracle from original row keys, not producer/engine results.
        rejected = {(r["game_id"], r["player_id"]) for r in rejections}
        facts = {
            (int(r.game_id), int(r.player_id)): (int(r.team_id), "played")
            for r in stats.loc[stats.minutes.gt(0)].itertuples()
        }
        for frame, state in [(old, None), (source, "did_not_play")]:
            for row in frame.itertuples():
                key = (int(row.game_id), int(row.player_id))
                if frame is source and key in rejected:
                    continue
                value = (int(row.team_id), state or row.participation_state)
                assert key not in facts or facts[key] == value
                facts[key] = value
        independent_full = {
            (tid, pid)
            for tid, pid in pairs
            if all((int(g), pid) in facts for g in teams.loc[teams.team_id.eq(tid), "game_id"])
        }
        assert independent_full == set(full)
        names = (
            pd.concat([stats, old, source])
            .drop_duplicates("player_id")
            .set_index("player_id")
            .player_name
        )
        queries = []
        for tid, pid in sorted(full):
            games = teams.loc[teams.team_id.eq(tid)]
            for word, state in [("with", "played"), ("without", "did_not_play")]:
                ids = {
                    int(g.game_id)
                    for g in games.itertuples()
                    if facts[int(g.game_id), pid] == (tid, state)
                }
                expected = games.loc[games.game_id.isin(ids)]
                query = f"{games.team_name.iloc[0]} record {word} {names[pid]} in {SEASON}"
                outcome = execute_natural_query(query)
                if not ids:
                    assert (outcome.result_status, outcome.result_reason) == (
                        "no_result",
                        "no_match",
                    ), query
                else:
                    assert outcome.result_status == "ok", (query, outcome.metadata)
                    sections = outcome.to_dict()["sections"]
                    summary = sections["summary"][0]
                    assert {r["game_id"] for r in sections["game_log"]} == ids, query
                    assert (summary["games"], summary["wins"], summary["losses"]) == (
                        len(ids),
                        int(expected.wl.eq("W").sum()),
                        int(expected.wl.eq("L").sum()),
                    )
                    assert summary["season_start"] == SEASON and summary["season_end"] == SEASON
                    assert summary["season_type"] == "Regular Season"
                queries.append(
                    dict(
                        query=query,
                        games=len(ids),
                        wins=int(expected.wl.eq("W").sum()),
                        losses=int(expected.wl.eq("L").sum()),
                        status=outcome.result_status,
                    )
                )
        assert len(queries) == 138
        # A rejected observation supplies no membership on either game side.
        from nbatools.commands._dated_membership import COLUMNS
        from nbatools.commands._participation_observations import game_participation

        for r in rejections:
            game = teams.loc[teams.game_id.eq(r["game_id"]) & teams.team_id.eq(r["team_id"])].iloc[
                0
            ]
            for tid, other in [
                (int(game.team_id), int(game.opponent_team_id)),
                (int(game.opponent_team_id), int(game.team_id)),
            ]:
                state, member = game_participation(
                    after,
                    pd.DataFrame(columns=COLUMNS),
                    r["player_id"],
                    r["game_id"],
                    tid,
                    pd.Timestamp(game.game_date).date(),
                    other_team=other,
                )
                if (r["game_id"], r["player_id"]) not in facts:
                    assert state == "unknown" and member.state == "unknown"
        output = (
            Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", tmp_path)) / "season-inactive-2024"
        )
        output.mkdir(parents=True, exist_ok=False)
        report = dict(
            classification="validated_staging_only_not_published",
            base_generation=GENERATION,
            base_manifest_sha256=MANIFEST,
            before=baseline,
            after=census,
            identity_name_rejections=rejections,
            complete_season_queries=queries,
            original_rows=len(source),
            accepted_rows=len(inactive),
            production_writes=0,
            verified_dated_intervals=0,
        )
        (output / "product-results.json").write_text(json.dumps(report, indent=2) + "\n")
        with ZipFile(output / "overlay.zip", "w", ZIP_DEFLATED) as archive:
            for path in root.rglob("*"):
                if path.is_file() and path.relative_to(root).as_posix() not in original:
                    archive.write(path, path.relative_to(root))
        with capfd.disabled():
            print(
                "SEASON_INACTIVE_2024_PRODUCT "
                + json.dumps(
                    dict(
                        before=baseline,
                        after=census,
                        accepted_rows=len(inactive),
                        quarantined_rows=len(rejections),
                        validated_queries=len(queries),
                        production_writes=0,
                    )
                ),
                flush=True,
            )
    finally:
        reset_data_source_cache()
        clear_frame_cache()
