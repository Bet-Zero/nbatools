"""Offline admission of the preserved partial readiness capture, never publication."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

import pandas as pd

from nbatools.commands.pipeline import pull_game_period_stats as periods
from nbatools.commands.pipeline import pull_games, pull_player_game_stats, pull_team_game_stats
from tools.build_readiness_recovery import ORIGINAL_ZIP_SHA256, PARENT_PATH, recovery_requirement
from tools.collection_bundle import unpack
from tools.qualify_rollover_q1 import CORE_SHA, EVIDENCE, _local_stage
from tools.stage_rollover_periods import import_window

ORACLE_SHA = "487b42ca27753f778be4be677021bd350dbd212b0837167abe9f7768c81c9d71"
REFRESH_SHA = "a0acf7bdc469fbef887b2ed1c12bc80e68e8bb8057fe9ffed08cf1cec53ce3a1"
PARTIAL = EVIDENCE / "partial-capture-20261103"


def _checked(path, sha):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError(f"Retained input differs: {path.name}")
    return raw


def retained_core():
    """Preserve all accepted81 cells; append only the separately retained seven games."""
    with zipfile.ZipFile(
        io.BytesIO(
            _checked(
                EVIDENCE / "readiness-reassessment/expanded-staging-acceptance-source.zip", CORE_SHA
            )
        )
    ) as z:
        frames = [
            pd.read_csv(
                io.BytesIO(z.read(f"acquired_data/expanded-core/staged-{grain}-game-logs.csv")),
                dtype={"GAME_ID": str},
            )
            for grain in ["player", "team"]
        ]
    with zipfile.ZipFile(
        io.BytesIO(_checked(EVIDENCE / "period-milestone/archive-refresh.zip", REFRESH_SHA))
    ) as z:
        from nbatools.commands.pipeline.structured_participation import _table

        names = [
            "playergamelogs-regular-season_base_totals.json",
            "leaguegamefinder-regular-season.json",
        ]
        for index, (name, table) in enumerate(
            zip(names, ["PlayerGameLogs", "LeagueGameFinderResults"], strict=True)
        ):
            fresh = _table(json.loads(z.read(name)), table)
            frames[index] = pd.concat(
                [frames[index], fresh[~fresh.GAME_ID.isin(frames[index].GAME_ID)]],
                ignore_index=True,
            )
    if len(frames[0]) != 1990 or len(frames[1]) != 176:
        raise ValueError("Retained88 context population differs")
    return frames


def qualify(output: Path, original_zip: Path | None = None):
    original_zip = original_zip or PARTIAL / "collection.zip"
    parent = json.loads(PARENT_PATH.read_text())
    _, ledger, _ = recovery_requirement(original_zip, parent, ORIGINAL_ZIP_SHA256)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    unpack(original_zip, parent, output / "original")
    original = output / "original"
    capture = json.loads((original / "acquisition.json").read_text())
    with zipfile.ZipFile(io.BytesIO(_checked(PARTIAL / "summary-oracles.zip", ORACLE_SHA))) as z:
        binding = json.loads(z.read("sources.json"))
        summaries = {}
        for item in binding["files"]:
            raw = z.read(item["file"])
            if (
                len(raw) != item["bytes"]
                or hashlib.sha256(raw).hexdigest() != item["sha256"]
                or hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
                != item["git_blob_sha"]
            ):
                raise ValueError("Summary original differs")
            summaries[item["game_id"]] = json.loads(raw)
    jobs = {}
    for item in capture["attempts"][:602]:
        params = item["parameters"]
        if "GameID" in params:
            key = (params["GameID"], params["StartPeriod"], params["EndPeriod"])
            jobs.setdefault(key, {})[item["endpoint"]] = (
                original / item["source_file"]
            ).read_bytes()
    # Independently qualified original Q1 is reused, never captured again.
    q1 = EVIDENCE / "q1-laptop-capture/collection.zip"
    _checked(q1, "ab6618b4b0da9ddd3f262547832718544d74de7cf24d67f4b7901cb9081ef88d")
    with zipfile.ZipFile(q1) as z:
        jobs[("0022600001", 1, 1)] = {
            endpoint: z.read(f"sources/{endpoint}_0022600001_q1.json")
            for endpoint in ["boxscoretraditionalv3", "boxscoreadvancedv3"]
        }
    frames = retained_core()
    root = output / "stage"
    root.mkdir()
    admitted, quarantined, waiting, player_frames, team_frames = [], [], [], [], []
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
        for (gid, start, end), bodies in sorted(jobs.items()):
            row = dict(
                game_id=gid,
                start_period=start,
                end_period=end,
                source_sha256={
                    name: hashlib.sha256(raw).hexdigest() for name, raw in bodies.items()
                },
            )
            if set(bodies) != {"boxscoretraditionalv3", "boxscoreadvancedv3"}:
                waiting.append(row)
                continue
            window = next(
                w for w in periods.PERIOD_WINDOWS if (w.start_period, w.end_period) == (start, end)
            )
            row.update(period_family=window.period_family, period_value=window.period_value)
            try:
                players, teams = import_window(
                    bodies["boxscoretraditionalv3"],
                    bodies["boxscoreadvancedv3"],
                    game_id=gid,
                    window=window,
                    summary=summaries[gid],
                    player_context=context[0],
                    team_context=context[1],
                )
            except ValueError as exc:
                row["error"] = str(exc)
                quarantined.append(row)
                continue
            row.update(player_rows=len(players), team_rows=len(teams))
            admitted.append(row)
            player_frames.append(players)
            team_frames.append(teams)
        for grain, outputs in [("player", player_frames), ("team", team_frames)]:
            path = root / f"data/raw/{grain}_game_period_stats/2026-27_regular_season.csv"
            path.parent.mkdir(parents=True)
            pd.concat(outputs, ignore_index=True).to_csv(path, index=False)
        # Actual existing consumers read only admitted windows, scoped to one game.
        from nbatools.commands.player_game_finder import build_result
        from nbatools.commands.team_record import build_team_record_result

        player = build_result(
            season="2026-27",
            player="Jayson Tatum",
            quarter="4",
            start_date="2026-10-20",
            end_date="2026-10-20",
        )
        team = build_team_record_result(
            team="BOS",
            season="2026-27",
            half="first",
            start_date="2026-10-20",
            end_date="2026-10-20",
        )
        rejected = build_result(
            season="2026-27",
            player="Naji Marshall",
            quarter="1",
            start_date=str(context[0].loc[context[0].game_id.eq(22600095), "game_date"].iloc[0]),
            end_date=str(context[0].loc[context[0].game_id.eq(22600095), "game_date"].iloc[0]),
        )
        if player.result_status != "ok" or team.result_status != "ok":
            raise ValueError("Required actual consumers did not answer")
        answers = dict(
            player=player.games.to_dict("records"),
            team=team.summary.to_dict("records"),
            quarantine_probe_status=rejected.result_status,
        )
    report = dict(
        classification="qualified_partial_windows_not_coherent_full_snapshot",
        original_zip_sha256=ORIGINAL_ZIP_SHA256,
        successful_source_responses=602,
        transport_missing=459,
        reused_prior_q1=True,
        admitted_windows=admitted,
        quarantined_windows=quarantined,
        waiting_windows=waiting,
        admitted_by_game=dict(Counter(x["game_id"] for x in admitted)),
        player_rows=sum(len(f) for f in player_frames),
        team_rows=sum(len(f) for f in team_frames),
        actual_answers=answers,
        successful_originals_preserved=ledger["retained_source_count"],
        full_snapshot_accepted=False,
        readiness_accepted=False,
        production_writes=0,
    )
    (output / "qualification.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    report = qualify(parser.parse_args().output)
    print(
        {
            key: (len(value) if key.endswith("_windows") else value)
            for key, value in report.items()
            if key not in ["admitted_by_game", "actual_answers"]
        }
    )
