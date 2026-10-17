"""Real-data contract: join a publicly reported ESPN game to pinned NBA rows.

Run explicitly through the existing read-only targeted R2 validation flow.
The source timestamp and a small collected CSV are evidence, not automatic
production publication or a claim that the whole NBA roster is complete.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.pipeline.pull_player_game_availability import (
    backfill,
    validate_publication,
)
from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]


def _stage_opening_game(tmp_path):
    season = "2025-26"
    suffix = f"{season}_regular_season.csv"
    source = {
        "games": data_read_csv(f"data/raw/games/{suffix}"),
        "team_game_stats": data_read_csv(f"data/raw/team_game_stats/{suffix}"),
        "player_game_stats": data_read_csv(f"data/raw/player_game_stats/{suffix}"),
    }
    game_log = source["games"]
    required = {"game_id", "game_date", "home_team_id", "away_team_id", "is_final"}
    assert required.issubset(game_log.columns), required - set(game_log.columns)
    target = game_log[
        game_log["game_date"].astype(str).eq("2025-10-21")
        & game_log["home_team_id"].eq(1610612747)
        & game_log["away_team_id"].eq(1610612744)
    ]
    assert len(target) == 1
    game = target.iloc[0]
    assert bool(game["is_final"])
    game_id = int(game["game_id"])

    scores = source["team_game_stats"]
    scoped = scores[pd.to_numeric(scores["game_id"], errors="raise").eq(game_id)]
    assert dict(zip(scoped.team_abbr, scoped.pts)) == {"LAL": 109, "GSW": 119}

    root = tmp_path / "data"
    for label, df in source.items():
        folder = root / "raw" / label
        folder.mkdir(parents=True)
        df.to_csv(folder / suffix, index=False)
    try:
        rosters = data_read_csv(f"data/raw/rosters/{season}.csv")
    except (FileNotFoundError, OSError):
        rosters = None
    if rosters is not None:
        roster_path = root / "raw/rosters"
        roster_path.mkdir(parents=True)
        rosters.to_csv(roster_path / f"{season}.csv", index=False)

    # Some source-listed inactives have no current-season appearances or were
    # absent from the later roster snapshot. Prior qualified rows resolve IDs;
    # only this game's report establishes their membership/nonparticipation.
    prior = data_read_csv("data/raw/player_game_stats/2024-25_regular_season.csv")
    prior.to_csv(root / "raw/player_game_stats/2024-25_regular_season.csv", index=False)

    return root, game_id


def test_2025_opening_lakers_warriors_explicit_dnp_and_nba_id_match(tmp_path):
    root, game_id = _stage_opening_game(tmp_path)
    rows = backfill("2025-26", root=root, source="espn", game_ids=[game_id])
    validate_publication(root)
    assert rows.game_id.eq(f"{game_id:010d}").all()
    assert rows.source.eq("espn_game_summary:401809244").all()
    assert rows.coverage_scope.eq("listed_player_rows_only").all()
    assert rows.team_id.isin([1610612747, 1610612744]).all()
    assert len(rows) >= 20
    assert rows.participation_state.eq("did_not_play").any()
    # The reported DNP is a source observation, not an invented injury or
    # an inference about athletes missing from the ESPN game box score.
    assert (
        rows.loc[rows.participation_state.eq("did_not_play"), "source_comment"]
        .str.startswith("DNP - ESPN confirmed")
        .all()
    )
    print(
        "Verified game-day observations:",
        len(rows),
        "source-reported DNP:",
        int(rows.participation_state.eq("did_not_play").sum()),
        "NBA IDs verified:",
        int(rows.player_id.nunique()),
    )


def test_official_opening_report_retains_real_source_and_explicit_absences(tmp_path):
    """Acquire one actual scorer report; retain publication inputs in CI evidence."""
    root, game_id = _stage_opening_game(tmp_path)
    evidence = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path / "evidence")))
    try:
        rows = backfill("2025-26", root=root, source="report", game_ids=[game_id])
    finally:
        # These are fetched NBA bytes and derived rows, never fixture data.
        # The existing validation workflow retains this directory as evidence;
        # an artifact is staging, not permanent R2 publication.
        for directory in ("player_game_availability_sources", "player_game_availability"):
            source = root / "raw" / directory
            if source.exists():
                shutil.copytree(source, evidence / "raw" / directory, dirs_exist_ok=True)
    validate_publication(root)
    assert rows.game_id.eq(f"{game_id:010d}").all()
    assert rows.source.eq("nba_official_finalbox:20251021_GSWLAL").all()
    assert rows.coverage_scope.eq("listed_player_rows_only").all()
    assert rows.team_id.isin([1610612747, 1610612744]).all()
    assert len(rows) == 34
    assert rows.participation_state.value_counts().to_dict() == {"played": 20, "did_not_play": 14}
    assert rows.groupby("team_abbr").size().to_dict() == {"GSW": 17, "LAL": 17}
    assert rows[rows.participation_state.eq("played")].groupby("team_abbr").size().to_dict() == {
        "GSW": 11,
        "LAL": 9,
    }
    assert rows.groupby("team_abbr").source_minutes.sum().to_dict() == pytest.approx(
        {"GSW": 240, "LAL": 240}
    )
    for name in (
        "LeBron James",
        "Moses Moody",
        "Bronny James",
        "Trayce Jackson-Davis",
        "Alex Toohey",
    ):
        player = rows[rows.player_name.eq(name)]
        assert len(player) == 1, name
        assert player.iloc[0].participation_state == "did_not_play", name
    receipt = evidence / "raw/player_game_availability_sources/20251021_GSWLAL.json"
    manifest = json.loads(receipt.read_text())
    assert rows.source_sha256.eq(manifest["sha256"]).all()
    import hashlib

    raw = receipt.parent / manifest["raw_file"]
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == manifest["sha256"]
    assert raw.stat().st_size == manifest["size_bytes"]
    assert manifest["source_url"].endswith("/20251021/20251021_GSWLAL.pdf")
    (evidence / "validation.json").write_text(
        json.dumps(
            {
                "game_id": f"{game_id:010d}",
                "base_generation": os.environ.get("NBATOOLS_DATA_GENERATION"),
                "candidate_sha": os.environ.get("VALIDATION_SHA"),
                "rows": len(rows),
                "source_receipt": str(receipt.relative_to(evidence)),
                "publication_state": "staged_only",
                "identity_source_sha256": rows.identity_source_sha256.fillna("").unique().tolist(),
            },
            indent=2,
        )
        + "\n"
    )
    print("Verified official report rows:", len(rows), "source SHA256:", manifest["sha256"])


def test_official_missing_player_profile_identity_sources(tmp_path):
    """Acquire a bounded official identity source; do not infer team membership."""
    import hashlib
    import urllib.request
    from datetime import UTC, datetime

    from nbatools.commands.pipeline.player_game_availability_profiles import profile_identity

    evidence = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path / "evidence")))
    directory = evidence / "raw/player_identity_sources"
    directory.mkdir(parents=True, exist_ok=True)
    expected = {1642893: "Alex Toohey", 1643024: "Chris Mañon"}
    for ident, name in expected.items():
        url = f"https://www.nba.com/player/{ident}"
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read(2_000_001)
        assert len(raw) <= 2_000_000
        digest = hashlib.sha256(raw).hexdigest()
        (directory / f"{digest}.html").write_bytes(raw)
        receipt = dict(
            source_url=url,
            retrieved_at=datetime.now(UTC).isoformat(),
            sha256=digest,
            size_bytes=len(raw),
            raw_file=f"{digest}.html",
        )
        (directory / f"{ident}.json").write_text(json.dumps(receipt, indent=2) + "\n")
        assert profile_identity(raw, ident, name) == name
        print("Verified official profile identity:", ident, name, digest)


def test_official_opening_report_qualified_absence_consumers(tmp_path, monkeypatch):
    """Source-derived DNP sample reaches record consumers with exact NBA values."""
    from nbatools.commands.data_utils import filter_without_player
    from nbatools.data_source import reset_data_source_cache
    from nbatools.query_service import execute_natural_query, execute_structured_query

    root, game_id = _stage_opening_game(tmp_path)
    evidence = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path / "evidence")))
    try:
        backfill("2025-26", root=root, source="report", game_ids=[game_id])
    finally:
        for directory in ("player_game_availability_sources", "player_game_availability"):
            source = root / "raw" / directory
            if source.exists():
                shutil.copytree(source, evidence / "raw" / directory, dirs_exist_ok=True)
    validate_publication(root)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.parent))
    # The local staging tree contains copies from the runner-pinned generation.
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    try:
        for team, name, wins, losses, points in [
            ("LAL", "LeBron James", 0, 1, 109),
            ("LAL", "LeBron James and Maxi Kleber", 0, 1, 109),
            ("GSW", "Moses Moody", 1, 0, 119),
        ]:
            result = execute_structured_query(
                "team_record",
                team=team,
                season="2025-26",
                without_player=name,
                start_date="2025-10-21",
                end_date="2025-10-21",
            )
            assert result.result_status == "ok", result.result_reason
            row = result.result.to_dict()["sections"]["summary"][0]
            assert (row["games"], row["wins"], row["losses"], row["pts_avg"]) == (
                1,
                wins,
                losses,
                points,
            )
        natural = execute_natural_query("Lakers record without LeBron James on October 21 2025")
        assert natural.result_status == "ok", natural.result_reason
        row = natural.result.to_dict()["sections"]["summary"][0]
        assert (row["games"], row["wins"], row["losses"], row["pts_avg"]) == (1, 0, 1, 109)
        teams = pd.read_csv(root / "raw/team_game_stats/2025-26_regular_season.csv")
        candidate = teams.loc[teams.game_id.eq(game_id) & teams.team_abbr.eq("LAL")]
        assert len(candidate) == 1
        assert filter_without_player(candidate, "Luka Dončić", ["2025-26"], "Regular Season").empty
        broader = teams.loc[teams.team_abbr.eq("LAL")]
        assert len(broader) > 1
        with pytest.raises(ValueError, match="coverage"):
            filter_without_player(broader, "LeBron James", ["2025-26"], "Regular Season")
    finally:
        reset_data_source_cache()


def _stage_celtics_lakers_reports(tmp_path):
    """Acquire four exact reports needed by S4; staging is not publication."""
    targets = {"2023-24": {22300403, 22300684}, "2025-26": {22500338, 22500823}}
    root = tmp_path / "data"
    evidence = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path / "evidence")))
    for season in targets:
        for kind in ("games", "team_game_stats", "player_game_stats"):
            path = f"raw/{kind}/{season}_regular_season.csv"
            frame = data_read_csv(f"data/{path}")
            destination = root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(destination, index=False)
        teams = pd.read_csv(root / f"raw/team_game_stats/{season}_regular_season.csv")
        actual = teams.loc[teams.team_abbr.eq("BOS") & teams.opponent_team_abbr.eq("LAL")]
        assert set(actual.game_id.astype(int)) == targets[season]
    for season in ("2022-23", "2024-25"):
        # Identity-only prior rows never supply participation or dated membership.
        frame = data_read_csv(f"data/raw/player_game_stats/{season}_regular_season.csv")
        frame.to_csv(root / f"raw/player_game_stats/{season}_regular_season.csv", index=False)

    observations = []
    try:
        for season, games in targets.items():
            rows = backfill(season, root=root, source="report", game_ids=sorted(games))
            assert set(rows.game_id.astype(int)) == games
            assert rows.coverage_scope.eq("listed_player_rows_only").all()
            assert rows.source.str.startswith("nba_official_finalbox:").all()
            assert rows.source_sha256.str.fullmatch(r"[0-9a-f]{64}").all()
            assert not rows.duplicated(["game_id", "player_id"]).any()
            assert rows.team_id.isin([1610612738, 1610612747]).all()
            canonical = pd.read_csv(root / f"raw/player_game_stats/{season}_regular_season.csv")
            canonical = canonical.loc[canonical.game_id.isin(games)]
            played = rows.loc[rows.participation_state.eq("played")]
            assert set(zip(played.game_id.astype(int), played.team_id, played.player_id)) == set(
                zip(canonical.game_id, canonical.team_id, canonical.player_id)
            )
            assert played.groupby(
                ["game_id", "team_id"]
            ).source_minutes.sum().tolist() == pytest.approx([240] * 4, abs=0.02)
            tatum = rows.loc[rows.player_id.eq(1628369)]
            assert set(tatum.game_id.astype(int)) == games
            assert tatum.team_id.eq(1610612738).all()
            state = "played" if season == "2023-24" else "did_not_play"
            assert tatum.participation_state.eq(state).all()
            if state == "did_not_play":
                assert tatum.source_comment.fillna("").str.len().gt(0).all()
            observations.append(rows)
        validate_publication(root)
    finally:
        # Retain raw evidence even on failure for diagnosis; never publish it here.
        for directory in ("player_game_availability_sources", "player_game_availability"):
            source = root / "raw" / directory
            if source.exists():
                shutil.copytree(source, evidence / "raw" / directory, dirs_exist_ok=True)
        for season, games in targets.items():
            for kind in ("games", "team_game_stats", "player_game_stats"):
                path = root / f"raw/{kind}/{season}_regular_season.csv"
                frame = pd.read_csv(path)
                target = evidence / "canonical_selected" / kind / path.name
                target.parent.mkdir(parents=True, exist_ok=True)
                frame.loc[frame.game_id.isin(games)].to_csv(target, index=False)
    all_rows = pd.concat(observations, ignore_index=True)
    print("Verified official report games:", sorted(all_rows.game_id.astype(int).unique().tolist()))
    print(
        "Explicit participation rows by season/state:",
        all_rows.groupby(["season", "participation_state"]).size().to_dict(),
    )

    return root


def test_official_celtics_lakers_reports_qualify_nonadjacent_season_participation(tmp_path):
    _stage_celtics_lakers_reports(tmp_path)
