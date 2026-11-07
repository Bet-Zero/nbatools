"""Source delta admission preserves accepted data and keeps missing periods explicit."""

import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

E = (
    Path(__file__).resolve().parents[1]
    / "working/nba-tools-completion-program/source-evidence/id18-current-required-20261107/current-required"
)
OLD = E.parent.parent / "core-live-current-20261107"
SUFFIX = "2026-27_regular_season.csv"
pytestmark = pytest.mark.served_seasons


def frame(z, family):
    return pd.read_csv(io.BytesIO(z.read(f"data/raw/{family}/{SUFFIX}")))


def test_qualified_new_roles_exact_source_keys_and_old_successes_survive():
    with (
        ZipFile(E / "normalized-required-stage.zip") as stage,
        ZipFile(OLD / "current123-provisional.zip") as old,
        ZipFile(E / "required-source-originals.zip") as source,
    ):
        for family in [
            "player_game_stats",
            "team_game_stats",
            "player_game_period_stats",
            "team_game_period_stats",
        ]:
            name = f"data/raw/{family}/{SUFFIX}"
            assert stage.read(name) == old.read(name)
        name = f"data/raw/player_game_starter_roles/{SUFFIX}"
        assert stage.read(name).startswith(old.read(name))
        roles = frame(stage, "player_game_starter_roles")
        new = roles.loc[roles.game_id.between(22600173, 22600188)]
        assert len(new) == 368 and new.role_source_trusted.eq(1).all()
        expected = {}
        appearances = frame(stage, "player_game_stats")
        for n in range(173, 189):
            gid = f"00226{n:05d}"
            box = json.loads(source.read(f"boxscoretraditionalv3-{gid}.json"))[
                "boxScoreTraditional"
            ]
            for side in ["homeTeam", "awayTeam"]:
                for p in box[side]["players"]:
                    expected[int(gid), box[side]["teamId"], p["personId"]] = int(
                        bool(p["position"].strip())
                    )
        positive = appearances.loc[appearances.game_id.between(22600173, 22600188)]
        wanted = {
            tuple(r)
            for r in positive[["game_id", "team_id", "player_id"]].itertuples(
                index=False, name=None
            )
        }
        actual = {(r.game_id, r.team_id, r.player_id): r.starter_flag for r in new.itertuples()}
        assert set(actual) == wanted
        assert actual == {k: expected[k] for k in wanted}
        assert new.groupby(["game_id", "team_id"]).starter_flag.sum().eq(5).all()
        before, after = frame(old, "games"), frame(stage, "games")
        selected = before.game_id.lt(22600173)
        pd.testing.assert_frame_equal(before.loc[selected], after.loc[selected], check_dtype=False)
        assert after.set_index("game_id").loc[[22600179, 22600186], "overtime_periods"].eq(1).all()
        period = frame(stage, "player_game_period_stats")
        assert period[["tov_pct", "usg_pct"]].isna().sum().to_dict() == {
            "tov_pct": 242,
            "usg_pct": 242,
        }


def test_fresh_family_coverage_and_numerical_basis_do_not_claim_complete_snapshot():
    q = json.loads((E / "qualification.json").read_bytes())
    assert (
        q["advanced_player_gp_w_l_keys"],
        q["advanced_team_gp_w_l_keys"],
        q["standings_w_l_keys"],
    ) == (452, 30, 30)
    assert len(q["source_player_ts_checks"]) == 452
    assert all(r["within_source3decimal"] for r in q["source_player_ts_checks"])
    assert q["structural_failures"] == {
        "player_game_period_stats": ["coverage missing 2208 requested keys"],
        "team_game_period_stats": ["coverage missing 192 requested keys"],
    }
    assert q["source_window_denominator"] == 745 and q["new_window_denominator"] == 98
    assert q["full_snapshot_accepted"] is q["freshness_accepted"] is False
    assert q["roster_membership_inference"] is False
    binding = json.loads((E / "source-binding.json").read_bytes())
    assert (
        hashlib.sha256((E / binding["archive"]).read_bytes()).hexdigest()
        == binding["archive_sha256"]
    )
    assert binding["old107body_requests"] == binding["production_writes"] == 0
