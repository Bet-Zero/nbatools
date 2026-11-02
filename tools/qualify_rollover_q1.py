"""Replay the immutable Q1 capture into isolated raw files and actual consumers.

No acquisition, production source configuration, publication or completeness flags.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import zipfile
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from nbatools.commands.pipeline import pull_games, pull_player_game_stats, pull_team_game_stats
from nbatools.commands.pipeline.pull_game_period_stats import PERIOD_WINDOWS
from tools.collect_rollover_q1_laptop import REQUEST
from tools.collection_bundle import unpack
from tools.stage_rollover_periods import import_window

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "working/nba-tools-completion-program/source-evidence/rollover-2026-27"
Q1_SHA = "ab6618b4b0da9ddd3f262547832718544d74de7cf24d67f4b7901cb9081ef88d"
CORE_SHA = "14781d501ae9afe85f6ae92a1b65053e22ffbe9b172b77b2bb25b6f66dbf3667"


@contextmanager
def _local_stage(root):
    from nbatools.commands._seasons import reset_latest_served_season_cache
    from nbatools.data_source import reset_data_source_cache

    names = dict(
        DATA_SOURCE="local", NBATOOLS_DATA_ROOT=str(root), NBATOOLS_DATA_GENERATION="legacy"
    )
    old = {name: os.environ.get(name) for name in names}
    cwd = Path.cwd()
    try:
        os.environ.update(names)
        os.chdir(root)
        reset_data_source_cache()
        reset_latest_served_season_cache()
        yield
    finally:
        os.chdir(cwd)
        for name, value in old.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        reset_data_source_cache()
        reset_latest_served_season_cache()


def qualify(output: Path):
    from nbatools.commands.player_game_finder import build_result
    from nbatools.commands.team_record import build_team_record_result

    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    archive = EVIDENCE / "q1-laptop-capture/collection.zip"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == Q1_SHA
    unpack(archive, REQUEST, output / "original")
    original = output / "original"
    capture = json.loads((original / "acquisition.json").read_text())
    assert capture["parameters"] == REQUEST["parameters"]
    assert capture["nba_api_version"] == "1.12.0"
    raw = []
    for endpoint, attempt in zip(REQUEST["endpoints"], capture["attempts"], strict=True):
        assert attempt["url"] == f"https://stats.nba.com/stats/{endpoint}"
        assert attempt["endpoint"] == endpoint and attempt["parameters"] == REQUEST["parameters"]
        assert attempt["http_status"] == 200 and attempt["response_complete"]
        assert attempt["attempts"] == 1 and not attempt.get("error_type")
        body = (original / attempt["source_file"]).read_bytes()
        assert len(body) == attempt["response_bytes"]
        assert hashlib.sha256(body).hexdigest() == attempt["response_sha256"]
        raw.append(body)
    core = EVIDENCE / "readiness-reassessment/expanded-staging-acceptance-source.zip"
    assert hashlib.sha256(core.read_bytes()).hexdigest() == CORE_SHA
    with zipfile.ZipFile(core) as z:
        frames = [
            pd.read_csv(
                io.BytesIO(z.read(f"acquired_data/expanded-core/staged-{grain}-game-logs.csv")),
                dtype={"GAME_ID": str},
            )
            for grain in ["player", "team"]
        ]
    with (EVIDENCE / "period-q1-0022600001/summary.json").open("rb") as z:
        summary_bytes = z.read()
    assert hashlib.sha256(summary_bytes).hexdigest() == REQUEST["oracle_summary_sha256"]
    root = output / "stage"
    root.mkdir()
    with _local_stage(root):
        pull_games.run("2026-27", "Regular Season", raw_frame=frames[1])
        pull_team_game_stats.run("2026-27", "Regular Season", raw_frame=frames[1])
        pull_player_game_stats.run("2026-27", "Regular Season", raw_frame=frames[0])
        context = [
            pd.read_csv(root / f"data/raw/{grain}_game_stats/2026-27_regular_season.csv")
            for grain in ["player", "team"]
        ]
        if "wl" not in context[0]:
            context[0] = context[0].merge(
                context[1][["game_id", "team_id", "wl"]],
                on=["game_id", "team_id"],
                validate="many_to_one",
            )
        players, teams = import_window(
            *raw,
            game_id="0022600001",
            window=PERIOD_WINDOWS[0],
            summary=json.loads(summary_bytes),
            player_context=context[0],
            team_context=context[1],
        )
        for grain, frame in [("player", players), ("team", teams)]:
            path = root / f"data/raw/{grain}_game_period_stats/2026-27_regular_season.csv"
            path.parent.mkdir(parents=True)
            frame.to_csv(path, index=False)
        answers = []
        for player in ["Cade Cunningham", "Jayson Tatum", "Kevin Huerter", "Luka Garza"]:
            result = build_result(
                season="2026-27",
                season_type="Regular Season",
                player=player,
                quarter="1",
                start_date="2026-10-20",
                end_date="2026-10-20",
            )
            assert result.result_status == "ok", (player, result)
            answers.append(dict(player=player, result=result.games.to_dict("records")))
        record = build_team_record_result(
            team="BOS",
            season="2026-27",
            quarter="1",
            start_date="2026-10-20",
            end_date="2026-10-20",
        )
        assert record.result_status == "ok", record
        answers.append(dict(team="BOS", result=record.summary.to_dict("records")))
        missing = build_result(
            season="2026-27",
            season_type="Regular Season",
            player="Cade Cunningham",
            quarter="2",
            start_date="2026-10-20",
            end_date="2026-10-20",
        )
        assert missing.result_status == "no_result"
    report = dict(
        classification="qualified_partial_q1_pipeline_and_consumer_not_full_snapshot",
        q1_zip_sha256=Q1_SHA,
        core_zip_sha256=CORE_SHA,
        observed_source_players=19,
        staged_player_rows=len(players),
        staged_team_rows=len(teams),
        windows=[["quarter", "1"]],
        zero_q1_player_ids=sorted(
            players.loc[players.minutes.eq(0), "player_id"].astype(int).tolist()
        ),
        answers=answers,
        unobserved_q2_consumer_status=missing.result_status,
        production_writes=0,
        full_snapshot_accepted=False,
        readiness_accepted=False,
    )
    (output / "qualification.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(qualify(parser.parse_args().output), indent=2, default=str))
