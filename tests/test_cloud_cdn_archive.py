"""A delayed supplemental event keeps its identity and its earlier source time."""

import pandas as pd
import pytest

from nbatools.commands.pipeline.build_clutch_stats import add_event_points
from nbatools.commands.pipeline.pull_play_by_play_events import normalize_play_by_play_events
from nbatools.commands.pipeline.validate_raw import validate_play_by_play_events_df
from tools.cloud_cdn_archive import selected_source


def _cdn_rows():
    rows = []
    for action, order, clock, home in [
        (545, 5450000, "PT10M42.00S", "91"),
        (547, 5305000, "PT11M19.00S", "87"),
        (548, 5480000, "PT10M42.00S", "92"),
    ]:
        rows.append(
            {
                "gameId": "22500003",
                "actionNumber": action,
                "orderNumber": order,
                "clock": clock,
                "period": 4,
                "teamId": "1610612752",
                "teamTricode": "NYK",
                "personId": "0",
                "playerName": "",
                "actionType": "test-event",
                "subType": "",
                "description": "controlled chronology fixture",
                "scoreHome": home,
                "scoreAway": "89",
            }
        )
    return pd.DataFrame(rows)


def _normalize(frame):
    return normalize_play_by_play_events(
        frame,
        season="2025-26",
        season_type="Regular Season",
        source="cdn.nba.com.liveData.playbyplay",
        source_schema_version="cdn_live_pbp.v1",
    )


def test_cdn_keeps_identity_and_uses_source_timeline():
    out = _normalize(_cdn_rows())
    assert out.action_number.tolist() == [547, 545, 548]
    assert out.source_order_number.tolist() == [5305000, 5450000, 5480000]
    assert out.score_home.tolist() == [87, 91, 92]
    assert out.pbp_source.eq("cdn.nba.com.liveData.playbyplay").all()
    # Sorting a delayed block by identity would invent a second score increase.
    points = add_event_points(out.iloc[::-1])
    assert points.action_number.tolist() == [547, 545, 548]
    assert points.pts.tolist() == [0, 4, 1]


def test_cdn_cannot_silently_fall_back_to_action_identity():
    with pytest.raises(ValueError, match="orderNumber"):
        _normalize(_cdn_rows().drop(columns="orderNumber"))
    out = _normalize(_cdn_rows()).drop(columns="source_order_number")
    with pytest.raises(ValueError, match="source_order_number"):
        validate_play_by_play_events_df(out)


def test_duplicate_cdn_chronology_is_rejected():
    frame = _cdn_rows()
    frame.loc[0, "orderNumber"] = frame.loc[1, "orderNumber"]
    with pytest.raises(ValueError, match="duplicated"):
        _normalize(frame)


def test_cdn_reversed_clock_or_score_is_rejected():
    for column, value in (("clock", "PT12M00.00S"), ("scoreHome", "80")):
        frame = _cdn_rows()
        frame.loc[0, column] = value
        with pytest.raises(ValueError, match="backward|decreases"):
            _normalize(frame)


def test_unpinned_archive_is_rejected_before_decompression():
    with pytest.raises(ValueError, match="checksum"):
        selected_source(b"untrusted")
