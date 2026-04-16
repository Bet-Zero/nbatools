import pytest

from nbatools.commands.format_output import format_pretty_output

pytestmark = pytest.mark.output

PLAYER_COMPARISON_RAW = """SUMMARY
player_name,games,wins,losses,win_pct,minutes_avg,pts_avg,reb_avg,ast_avg,stl_avg,blk_avg,fg3m_avg,plus_minus_avg,efg_pct_avg,ts_pct_avg,pts_sum,reb_sum,ast_sum
Nikola Jokić,10,9,1,0.9,36.1,24.0,13.6,12.7,0.7,0.8,1.3,8.3,0.602,0.63,240,136,127
Joel Embiid,10,8,2,0.8,33.2,29.4,8.1,4.5,0.4,1.3,2.1,4.9,0.552,0.621,294,81,45

COMPARISON
metric,Nikola Jokić,Joel Embiid
games,10,10
wins,9,8
losses,1,2
win_pct,0.9,0.8
minutes_avg,36.1,33.2
pts_avg,24.0,29.4
reb_avg,13.6,8.1
ast_avg,12.7,4.5
stl_avg,0.7,0.4
blk_avg,0.8,1.3
fg3m_avg,1.3,2.1
plus_minus_avg,8.3,4.9
efg_pct_avg,0.602,0.552
ts_pct_avg,0.63,0.621
pts_sum,240,294
reb_sum,136,81
ast_sum,127,45
"""

PLAYER_SPLIT_RAW = """SUMMARY
player_name,season_start,season_end,season_type,split,games_total
Nikola Jokić,2025-26,2025-26,Regular Season,home_away,62

SPLIT_COMPARISON
bucket,games,wins,losses,win_pct,minutes_avg,pts_avg,reb_avg,ast_avg,stl_avg,blk_avg,fg3m_avg,efg_pct_avg,ts_pct_avg,plus_minus_avg
home,31,22,9,0.71,34.419,27.806,12.452,11.194,1.387,0.774,1.581,0.638,0.68,9.032
away,31,18,13,0.581,35.677,27.903,13.29,10.516,1.355,0.839,1.968,0.651,0.695,7.742
"""

TEAM_SPLIT_RAW = """SUMMARY
team_name,season_start,season_end,season_type,split,games_total
Boston Celtics,2025-26,2025-26,Regular Season,wins_losses,77

SPLIT_COMPARISON
bucket,games,wins,losses,win_pct,pts_avg,reb_avg,ast_avg,stl_avg,blk_avg,fg3m_avg,tov_avg,efg_pct_avg,ts_pct_avg,plus_minus_avg
wins,52,52,0,1,120.385,47.865,26.596,6.962,5.327,16.577,10.981,0.58,0.609,15.558
losses,25,0,25,0,102.68,43.68,20.36,7.36,4.64,12.68,12.2,0.492,0.525,-9.12
"""

PLAYER_SUMMARY_RAW = """SUMMARY
player_name,season_start,season_end,season_type,games,wins,losses,win_pct,minutes_avg,minutes_sum,pts_avg,pts_sum,reb_avg,reb_sum,ast_avg,ast_sum,efg_pct_avg,efg_pct_sum,ts_pct_avg,ts_pct_sum
Nikola Jokić,2025-26,2025-26,Regular Season,10,9,1,0.9,36.1,361,24,240,13.6,136,12.7,127,0.602,6.02,0.63,6.3

BY_SEASON
season,games,wins,losses,pts_avg,reb_avg,ast_avg,minutes_avg,efg_pct_avg,ts_pct_avg
2025-26,10,9,1,24,13.6,12.7,36.1,0.602,0.63
"""

TABLE_RAW = """rank,season,season_type,game_date,player_name,team_abbr,opponent_team_abbr,pts,reb,ast,fg3m,wl
1,2025-26,Regular Season,2026-04-01,Nikola Jokić,DEN,MIN,30,14,12,2,W
2,2025-26,Regular Season,2026-03-29,Nikola Jokić,DEN,LAL,24,11,10,1,W
"""


def test_format_player_comparison_pretty():
    out = format_pretty_output(PLAYER_COMPARISON_RAW, "Jokic vs Embiid recent form")
    assert 'Query: "Jokic vs Embiid recent form"' in out
    assert "Nikola Jokić vs Joel Embiid" in out
    assert "Comparison Table" in out
    assert "Games" in out
    assert "eFG%" in out
    assert "TS%" in out
    assert "PTS Total" in out
    assert "────────────────────────" in out


def test_format_player_split_pretty():
    out = format_pretty_output(PLAYER_SPLIT_RAW, "Jokic home vs away in 2025-26")
    assert 'Query: "Jokic home vs away in 2025-26"' in out
    assert "Nikola Jokić" in out
    assert "Split: Home vs Away" in out
    assert "Home vs Away" in out
    assert "Split Table" in out
    assert "Home" in out
    assert "Away" in out
    assert "eFG%" in out
    assert "TS%" in out


def test_format_team_split_pretty():
    out = format_pretty_output(TEAM_SPLIT_RAW, "Celtics wins vs losses")
    assert 'Query: "Celtics wins vs losses"' in out
    assert "Boston Celtics" in out
    assert "Split: Wins vs Losses" in out
    assert "Wins vs Losses" in out
    assert "Split Table" in out
    assert "Wins" in out
    assert "Losses" in out
    assert "TOV" in out


def test_format_summary_with_by_season():
    out = format_pretty_output(PLAYER_SUMMARY_RAW, "Jokic recent form")
    assert 'Query: "Jokic recent form"' in out
    assert "Nikola Jokić" in out
    assert "Averages" in out
    assert "By Season" in out
    assert "PTS 24" in out
    assert "eFG% 0.602" in out
    assert "TS% 0.63" in out


def test_format_ranked_table_pretty():
    out = format_pretty_output(TABLE_RAW, "Jokic last 2 games")
    assert 'Query: "Jokic last 2 games"' in out
    assert "Rows returned: 2" in out
    assert "Nikola Jokić" in out
    assert "2025-26" in out
    assert "pts" in out.lower() or "PTS" in out


def test_format_no_matching_games_passthrough():
    raw = "SUMMARY\nno matching games\n"
    out = format_pretty_output(raw, "unknown query")
    assert "no matching games" in out.lower()
