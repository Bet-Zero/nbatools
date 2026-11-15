"""Product acceptance of one retained season batch; no network acquisition."""

import hashlib
import io
import json
import os
from collections import Counter
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import pytest

from nbatools.commands._dated_membership import COLUMNS, load_membership
from nbatools.commands._participation_observations import combined_observations, game_participation
from nbatools.commands.pipeline.pull_player_game_availability import validate_publication
from nbatools.commands.pipeline.structured_participation import stage_season_inactive
from nbatools.data_source import data_generation_context, data_path, reset_data_source_cache
from nbatools.dataframe_cache import clear_frame_cache
from nbatools.query_service import execute_natural_query
from tools.stage_participation_collection import build_stage

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
PROGRAM = Path(__file__).resolve().parents[1] / "working/nba-tools-completion-program"
EVIDENCE = PROGRAM / "source-evidence/season-inactive-pilot-20261115"
GENERATION = "availability-participation-2025-durant-v1-20261114"
MANIFEST = "cde98408f3390e6191da564197fb77ffbc598a3059963cfc21d9f2d7e1a6b366"
AVAILABILITY = "raw/player_game_availability/2023-24_regular_season.csv"


def _census(observations, teams, pairs, processed_games):
    """Count complete 82-game cases, not individual known rows or with-only logs."""
    empty = pd.DataFrame(columns=COLUMNS)
    totals, complete = Counter(), {}
    blocked_omission, blocked_other = 0, 0
    for tid, pid in sorted(pairs):
        games = teams.loc[teams.team_id.eq(tid)]
        assert len(games) == 82
        rows = observations.loc[observations.player_id.eq(pid)]
        states, unknowns, omitted = Counter(), [], False
        for game in games.itertuples():
            state, member = game_participation(
                rows,
                empty,
                pid,
                int(game.game_id),
                tid,
                pd.Timestamp(game.game_date).date(),
                other_team=int(game.opponent_team_id),
            )
            states[state] += 1
            if state == "unknown":
                unknowns.append(int(game.game_id))
                omitted |= int(game.game_id) in processed_games
                assert member.state == "unknown"  # joint gap, never invented tenure/DNP
        totals.update(states)
        if not unknowns:
            complete[tid, pid] = dict(states)
        elif omitted:
            blocked_omission += 1
        else:
            blocked_other += 1
    return dict(
        candidate_cases=len(pairs),
        complete_cases=len(complete),
        states=dict(totals),
        blocked_with_processed_game_omission=blocked_omission,
        blocked_only_outside_processed_game_population=blocked_other,
    ), complete


def test_retained_season_batch_unlocks_complete_season_answers(tmp_path, monkeypatch, capfd):
    # The authenticated run must compare against the actual current generation,
    # not silently call an old pinned snapshot today's published baseline.
    if os.environ.get("DATA_SOURCE") == "r2":
        from nbatools.data_source import _get_data_source

        assert _get_data_source().active_generation() == GENERATION
    with data_generation_context() as generation:
        assert generation == GENERATION
        manifest = data_path("data/metadata/generation_manifest.json").read_bytes()
        assert hashlib.sha256(manifest).hexdigest() == MANIFEST
        entries = {e["path"]: e for e in json.loads(manifest)["files"]}
        assert not any(p.startswith("raw/player_team_membership/") for p in entries)
        raw_inputs = {}
        for path in [
            AVAILABILITY,
            "raw/rosters/2023-24.csv",
            *[
                f"raw/{kind}/2023-24_regular_season.csv"
                for kind in ["games", "team_game_stats", "player_game_stats"]
            ],
        ]:
            raw = data_path("data/" + path).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == entries[path]["sha256"]
            raw_inputs[path] = raw
        before_obs, _ = combined_observations(["2023-24"], "Regular Season")
        request = PROGRAM / "source-evidence/league-participation-20261114/game-request.json"
        build_stage(
            request,
            PROGRAM / "source-evidence/k08-tatum-2023",
            tmp_path / "prior",
            tmp_path / "prior-overlay",
            candidate_sha=os.environ["VALIDATION_SHA"],
        )
    root = tmp_path / "prior/data"
    teams = pd.read_csv(io.BytesIO(raw_inputs["raw/team_game_stats/2023-24_regular_season.csv"]))
    stats = pd.read_csv(io.BytesIO(raw_inputs["raw/player_game_stats/2023-24_regular_season.csv"]))
    old = pd.read_csv(io.BytesIO(raw_inputs[AVAILABILITY]))
    roster = pd.read_csv(io.BytesIO(raw_inputs["raw/rosters/2023-24.csv"]))
    pairs = {
        (int(t), int(p))
        for frame in (stats, old, roster)
        for t, p in zip(frame.team_id, frame.player_id)
    }
    with ZipFile(PROGRAM / "source-evidence/team-membership-20261114/originals.zip") as z:
        movements = json.loads(z.read("player-movement.json"))["NBA_Player_Movement"]["rows"]
    for move in movements:
        if (
            not "2023-10-23" <= move["TRANSACTION_DATE"][:10] <= "2024-04-14"
            or not move["PLAYER_ID"]
        ):
            continue
        pairs.add((int(move["TEAM_ID"]), int(move["PLAYER_ID"])))
        if move["Transaction_Type"] == "Trade":
            pairs.add((int(move["Additional_Sort"]), int(move["PLAYER_ID"])))
    assert len(pairs) == 713  # candidate identities only; no membership inferred
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.parent))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    clear_frame_cache()
    try:
        prior_obs, _ = combined_observations(["2023-24"], "Regular Season")
        existing = {
            p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()
        }
        receipt = json.loads((EVIDENCE / "source.json").read_bytes())
        with ZipFile(
            PROGRAM / "source-evidence/league-participation-20261114/bulk-inactive-original.zip"
        ) as z:
            raw = z.read("game_rosters_2024.csv")
        assert hashlib.sha256(raw).hexdigest() == receipt["sha256"]
        inactive = stage_season_inactive(root, raw, receipt, "2023-24")
        assert len(inactive) == 11010 and inactive.game_id.nunique() == 1230
        assert set(zip(inactive.team_id, inactive.player_id)) <= pairs
        assert all((root / path).read_bytes() == body for path, body in existing.items())
        assert len(pd.read_csv(root / AVAILABILITY)) == 875
        validate_publication(root)
        clear_frame_cache()
        observations, _ = combined_observations(["2023-24"], "Regular Season")
        assert load_membership(["2023-24"]).empty
        phases, full = {}, {}
        for label, observed, processed, expected in [
            ("published", before_obs, set(old.game_id), 18),
            ("prior_pr619", prior_obs, set(pd.read_csv(root / AVAILABILITY).game_id), 19),
            ("retained_batch", observations, set(pd.read_csv(root / AVAILABILITY).game_id), 93),
        ]:
            phases[label], full[label] = _census(observed, teams, pairs, processed)
            assert phases[label]["complete_cases"] == expected
        assert phases["retained_batch"]["states"] == {
            "played": 26283,
            "did_not_play": 11109,
            "not_member": 228,
            "unknown": 20846,
        }
        assert len({t for t, p in full["retained_batch"]}) == 27
        assert not any(
            all((t, p) in full["retained_batch"] for t, p in pairs if t == tid)
            for tid in teams.team_id.unique()
        )  # no claim of complete coverage of every candidate on an entire club
        # Independent oracle: direct archived source keys, never app calculation.
        facts = {
            (int(r.game_id), int(r.player_id)): (int(r.team_id), "played")
            for r in stats.loc[stats.minutes.gt(0)].itertuples()
        }
        raw_inactive = pd.read_csv(io.BytesIO(raw))
        raw_inactive = raw_inactive.loc[raw_inactive.season_type_id.eq(2)].copy()
        raw_inactive["participation_state"] = "did_not_play"
        raw_inactive["player_name"] = raw_inactive.first_name + " " + raw_inactive.last_name
        for frame in (old, raw_inactive):
            for row in frame.itertuples():
                key, value = (
                    (int(row.game_id), int(row.player_id)),
                    (int(row.team_id), row.participation_state),
                )
                assert key not in facts or facts[key] == value
                facts[key] = value
        source = PROGRAM / "source-evidence/k08-tatum-2023/sources"
        for item in json.loads(request.read_bytes())["requirements"]:
            gid = int(item["game_id"])
            native = json.loads((source / f"boxscoretraditionalv3_{gid:010d}.json").read_bytes())[
                "boxScoreTraditional"
            ]
            for side in ["homeTeam", "awayTeam"]:
                for person in native[side]["players"]:
                    clock = person["statistics"]["minutes"]
                    if clock and sum(map(float, clock.split(":"))) > 0:
                        state = "played"
                    elif person["comment"].startswith(("DNP", "DND", "NWT", "INACTIVE")):
                        state = "did_not_play"
                    else:
                        continue
                    key, value = (
                        (gid, int(person["personId"])),
                        (int(native[side]["teamId"]), state),
                    )
                    assert key not in facts or facts[key] == value
                    facts[key] = value
        independent_full = {
            (tid, pid)
            for tid, pid in pairs
            if all((int(gid), pid) in facts for gid in teams.loc[teams.team_id.eq(tid), "game_id"])
        }
        assert independent_full == set(full["retained_batch"])
        names = (
            pd.concat([stats, old, raw_inactive])
            .drop_duplicates("player_id")
            .set_index("player_id")
            .player_name
        )
        query_checks = []
        for (tid, pid), states in full["retained_batch"].items():
            games = teams.loc[teams.team_id.eq(tid)]
            assert all((int(g.game_id), pid) in facts for g in games.itertuples())
            team_name = games.team_name.iloc[0]
            for word, state in [("with", "played"), ("without", "did_not_play")]:
                ids = {
                    int(g.game_id)
                    for g in games.itertuples()
                    if facts[int(g.game_id), pid] == (tid, state)
                }
                expected = games.loc[games.game_id.isin(ids)]
                query = f"{team_name} record {word} {names[pid]} in 2023-24"
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
                    ), query
                query_checks.append(
                    dict(
                        query=query,
                        games=len(ids),
                        wins=int(expected.wl.eq("W").sum()),
                        losses=int(expected.wl.eq("L").sum()),
                        status=outcome.result_status,
                    )
                )
        assert len(query_checks) == 186
        # Acquired/traded/late-signed identities cannot inherit missing games.
        for query in [
            "Rockets record without Steven Adams in 2023-24",
            "Lakers record without Spencer Dinwiddie in 2023-24",
        ]:
            outcome = execute_natural_query(query)
            assert (outcome.result_status, outcome.result_reason) == ("no_result", "unsupported")
        output = (
            Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", tmp_path)) / "season-inactive-pilot"
        )
        output.mkdir(parents=True, exist_ok=False)
        report = dict(
            classification="validated_staging_only_not_published",
            base_generation=GENERATION,
            base_manifest_sha256=MANIFEST,
            phases=phases,
            complete_season_queries=query_checks,
            new_game_source_requests=0,
            verified_dated_intervals=0,
            all_remaining_unknowns_have_unresolved_membership_and_participation=True,
        )
        (output / "product-results.json").write_text(json.dumps(report, indent=2) + "\n")
        with ZipFile(output / "overlay.zip", "w", ZIP_DEFLATED) as archive:
            for path in (tmp_path / "prior-overlay").rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(tmp_path / "prior-overlay"))
            for path in root.rglob("*"):
                if path.is_file() and path.relative_to(root).as_posix() not in existing:
                    archive.write(path, path.relative_to(root))
        with ZipFile(output / "overlay.zip") as archive:
            inventory = {n: hashlib.sha256(archive.read(n)).hexdigest() for n in archive.namelist()}
        with capfd.disabled():
            print(
                "SEASON_INACTIVE_PRODUCT "
                + json.dumps(
                    dict(
                        phases=phases,
                        validated_queries=len(query_checks),
                        publication_state="staged_only_no_writes",
                        overlay_file_sha256=inventory,
                    )
                ),
                flush=True,
            )
    finally:
        reset_data_source_cache()
        clear_frame_cache()
