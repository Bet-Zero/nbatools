import json
from contextlib import redirect_stdout
from io import StringIO

from nbatools.cli_apps.queries import _run_and_handle_exports
from nbatools.commands.format_output import (
    METADATA_LABEL,
    parse_labeled_sections,
    parse_metadata_block,
)
from nbatools.commands.game_finder import run as game_finder_run
from nbatools.commands.game_summary import run as game_summary_run
from nbatools.commands.natural_query import run as natural_query_run
from nbatools.commands.player_compare import run as player_compare_run
from nbatools.commands.player_game_finder import run as player_game_finder_run
from nbatools.commands.player_game_summary import run as player_game_summary_run
from nbatools.commands.player_split_summary import run as player_split_summary_run
from nbatools.commands.player_streak_finder import run as player_streak_finder_run
from nbatools.commands.season_leaders import run as season_leaders_run
from nbatools.commands.team_compare import run as team_compare_run
from nbatools.commands.team_split_summary import run as team_split_summary_run
from nbatools.commands.top_player_games import run as top_player_games_run


def _capture_output(func, *args, **kwargs) -> str:
    buffer = StringIO()
    with redirect_stdout(buffer):
        func(*args, **kwargs)
    return buffer.getvalue()


def test_top_player_games_smoke():
    out = _capture_output(
        top_player_games_run,
        season="2005-06",
        stat="pts",
        limit=5,
        season_type="Regular Season",
        ascending=False,
    )
    assert "player_name" in out
    assert "Kobe Bryant" in out
    assert "2005-06" in out


def test_season_leaders_smoke():
    out = _capture_output(
        season_leaders_run,
        season="2023-24",
        stat="ast",
        limit=5,
        season_type="Regular Season",
        min_games=20,
        ascending=False,
    )
    assert "ast_per_game" in out
    assert "Tyrese Haliburton" in out
    assert "2023-24" in out


def test_game_finder_multiseason_smoke():
    out = _capture_output(
        game_finder_run,
        season=None,
        start_season="2021-22",
        end_season="2023-24",
        season_type="Regular Season",
        team="BOS",
        opponent="MIL",
        home_only=True,
        away_only=False,
        wins_only=True,
        losses_only=False,
        stat=None,
        min_value=None,
        max_value=None,
        limit=10,
        sort_by="game_date",
        ascending=False,
        last_n=None,
    )
    assert "team_name" in out
    assert "Boston Celtics" in out
    assert "MIL" in out


def test_player_game_summary_smoke():
    out = _capture_output(
        player_game_summary_run,
        season="2005-06",
        start_season=None,
        end_season=None,
        season_type="Regular Season",
        player="Kobe Bryant",
        team=None,
        opponent="DAL",
        home_only=False,
        away_only=False,
        wins_only=False,
        losses_only=False,
        stat="pts",
        min_value=40,
        max_value=None,
        last_n=None,
    )
    assert "SUMMARY" in out
    assert "BY_SEASON" in out
    assert "Kobe Bryant" in out


def test_game_summary_advanced_stats_smoke():
    out = _capture_output(
        game_summary_run,
        season=None,
        start_season="2021-22",
        end_season="2023-24",
        season_type="Regular Season",
        team="BOS",
        opponent=None,
        home_only=False,
        away_only=False,
        wins_only=False,
        losses_only=False,
        stat=None,
        min_value=None,
        max_value=None,
        last_n=None,
    )
    assert "efg_pct_avg" in out
    assert "ts_pct_avg" in out
    assert "SUMMARY" in out


def test_player_summary_advanced_stats_smoke():
    out = _capture_output(
        player_game_summary_run,
        season="2008-09",
        start_season=None,
        end_season=None,
        season_type="Playoffs",
        player="Kobe Bryant",
        team=None,
        opponent=None,
        home_only=False,
        away_only=False,
        wins_only=False,
        losses_only=False,
        stat=None,
        min_value=None,
        max_value=None,
        last_n=None,
    )
    assert "efg_pct_avg" in out
    assert "ts_pct_avg" in out
    assert "Kobe Bryant" in out


def test_player_summary_new_advanced_metrics_smoke():
    out = _capture_output(
        player_game_summary_run,
        season="2025-26",
        start_season=None,
        end_season=None,
        season_type="Regular Season",
        player="Nikola Jokić",
        team=None,
        opponent=None,
        home_only=False,
        away_only=False,
        wins_only=False,
        losses_only=False,
        stat=None,
        min_value=None,
        max_value=None,
        last_n=10,
    )
    assert "usg_pct_avg" in out
    assert "ast_pct_avg" in out
    assert "reb_pct_avg" in out


def test_player_compare_smoke():
    out = _capture_output(
        player_compare_run,
        player_a="Kobe Bryant",
        player_b="LeBron James",
        season="2005-06",
        start_season=None,
        end_season=None,
        season_type="Regular Season",
        team=None,
        opponent=None,
        home_only=False,
        away_only=False,
        wins_only=False,
        losses_only=False,
        last_n=None,
    )
    assert "SUMMARY" in out
    assert "COMPARISON" in out
    assert "Kobe Bryant" in out
    assert "LeBron James" in out


def test_player_compare_advanced_stats_smoke():
    out = _capture_output(
        player_compare_run,
        player_a="Kobe Bryant",
        player_b="LeBron James",
        season="2008-09",
        start_season=None,
        end_season=None,
        season_type="Playoffs",
        team=None,
        opponent=None,
        home_only=False,
        away_only=False,
        wins_only=False,
        losses_only=False,
        last_n=None,
    )
    assert "efg_pct_avg" in out
    assert "ts_pct_avg" in out
    assert "Kobe Bryant" in out
    assert "LeBron James" in out


def test_player_compare_new_advanced_metrics_smoke():
    out = _capture_output(
        player_compare_run,
        player_a="Nikola Jokić",
        player_b="Joel Embiid",
        season="2025-26",
        start_season=None,
        end_season=None,
        season_type="Regular Season",
        team=None,
        opponent=None,
        home_only=False,
        away_only=False,
        wins_only=False,
        losses_only=False,
        last_n=10,
    )
    assert "usg_pct_avg" in out
    assert "ast_pct_avg" in out
    assert "reb_pct_avg" in out


def test_team_compare_smoke():
    out = _capture_output(
        team_compare_run,
        team_a="BOS",
        team_b="MIL",
        season=None,
        start_season="2021-22",
        end_season="2023-24",
        season_type="Regular Season",
        opponent=None,
        home_only=False,
        away_only=False,
        wins_only=False,
        losses_only=False,
        last_n=None,
    )
    assert "SUMMARY" in out
    assert "COMPARISON" in out
    assert "BOS" in out
    assert "MIL" in out


def test_team_compare_advanced_stats_smoke():
    out = _capture_output(
        team_compare_run,
        team_a="BOS",
        team_b="MIL",
        season=None,
        start_season="2021-22",
        end_season="2023-24",
        season_type="Regular Season",
        opponent=None,
        home_only=False,
        away_only=False,
        wins_only=False,
        losses_only=False,
        last_n=None,
    )
    assert "efg_pct_avg" in out
    assert "ts_pct_avg" in out


def test_player_split_summary_smoke():
    out = _capture_output(
        player_split_summary_run,
        split="home_away",
        season="2025-26",
        start_season=None,
        end_season=None,
        season_type="Regular Season",
        player="Nikola Jokić",
        team=None,
        opponent=None,
        stat=None,
        min_value=None,
        max_value=None,
        last_n=None,
    )
    assert "SUMMARY" in out
    assert "SPLIT_COMPARISON" in out
    assert "Nikola Jokić" in out
    assert "home" in out
    assert "away" in out


def test_player_split_summary_new_advanced_metrics_smoke():
    out = _capture_output(
        player_split_summary_run,
        split="home_away",
        season="2025-26",
        start_season=None,
        end_season=None,
        season_type="Regular Season",
        player="Nikola Jokić",
        team=None,
        opponent=None,
        stat=None,
        min_value=None,
        max_value=None,
        last_n=None,
    )
    assert "usg_pct_avg" in out
    assert "ast_pct_avg" in out
    assert "reb_pct_avg" in out


def test_team_split_summary_smoke():
    out = _capture_output(
        team_split_summary_run,
        split="wins_losses",
        season="2025-26",
        start_season=None,
        end_season=None,
        season_type="Regular Season",
        team="BOS",
        opponent=None,
        stat=None,
        min_value=None,
        max_value=None,
        last_n=None,
    )
    assert "SUMMARY" in out
    assert "SPLIT_COMPARISON" in out
    assert "Boston Celtics" in out
    assert "wins" in out
    assert "losses" in out


def test_natural_query_pretty_smoke():
    out = _capture_output(
        natural_query_run,
        query="Kobe 40 point games summary vs Dallas in 2005-06",
        pretty=True,
    )
    assert 'Query: "Kobe 40 point games summary vs Dallas in 2005-06"' in out
    assert "Kobe Bryant" in out
    assert "Record: 2-0" in out


def test_natural_query_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="season leaders in assists for 2023-24 playoffs",
        pretty=False,
    )
    assert "player_name" in out
    assert "ast_per_game" in out
    assert "Playoffs" in out


def test_natural_comparison_pretty_smoke():
    out = _capture_output(
        natural_query_run,
        query="Kobe vs LeBron playoffs in 2008-09",
        pretty=True,
    )
    assert 'Query: "Kobe vs LeBron playoffs in 2008-09"' in out
    assert "Kobe Bryant vs LeBron James" in out
    assert "Comparison Table" in out
    assert "PTS:" in out


def test_natural_comparison_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="Kobe vs LeBron playoffs in 2008-09",
        pretty=False,
    )
    assert "SUMMARY" in out
    assert "COMPARISON" in out
    assert "Kobe Bryant" in out
    assert "LeBron James" in out


def test_natural_team_comparison_pretty_smoke():
    out = _capture_output(
        natural_query_run,
        query="Celtics vs Bucks from 2021-22 to 2023-24",
        pretty=True,
    )
    assert 'Query: "Celtics vs Bucks from 2021-22 to 2023-24"' in out
    assert "BOS vs MIL" in out
    assert "Comparison Table" in out
    assert "PTS:" in out


def test_natural_team_comparison_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="Celtics vs Bucks from 2021-22 to 2023-24",
        pretty=False,
    )
    assert "SUMMARY" in out
    assert "COMPARISON" in out
    assert "BOS" in out
    assert "MIL" in out


def test_natural_player_comparison_shows_advanced_stats_pretty():
    out = _capture_output(
        natural_query_run,
        query="Kobe vs LeBron playoffs in 2008-09",
        pretty=True,
    )
    assert "eFG%:" in out
    assert "TS%:" in out


def test_natural_team_comparison_shows_advanced_stats_pretty():
    out = _capture_output(
        natural_query_run,
        query="Celtics vs Bucks from 2021-22 to 2023-24",
        pretty=True,
    )
    assert "eFG%:" in out
    assert "TS%:" in out


def test_recent_form_player_summary_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic recent form",
        pretty=True,
    )
    assert 'Query: "Jokic recent form"' in out
    assert "Nikola Jokić" in out
    assert "Games: 10" in out
    assert "By Season" in out


def test_recent_form_player_summary_shows_new_advanced_metrics():
    out = _capture_output(
        natural_query_run,
        query="Jokic recent form",
        pretty=True,
    )
    assert "USG%" in out
    assert "AST%" in out
    assert "REB%" in out


def test_recent_form_player_summary_v2_values_are_percent_scale():
    out = _capture_output(
        natural_query_run,
        query="Jokic recent form",
        pretty=True,
    )
    assert "USG% 27." in out or "USG% 28." in out or "USG% 26." in out
    assert "AST% 51." in out or "AST% 50." in out or "AST% 52." in out
    assert "REB% 20." in out or "REB% 19." in out or "REB% 21." in out


def test_recent_form_team_summary_smoke():
    out = _capture_output(
        natural_query_run,
        query="Celtics recent form",
        pretty=True,
    )
    assert 'Query: "Celtics recent form"' in out
    assert "Boston Celtics" in out
    assert "Games: 10" in out
    assert "By Season" in out


def test_recent_form_player_comparison_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic vs Embiid recent form",
        pretty=True,
    )
    assert 'Query: "Jokic vs Embiid recent form"' in out
    assert "Nikola Jokić vs Joel Embiid" in out
    assert "Games: 10 vs 10" in out
    assert "Comparison Table" in out


def test_recent_form_player_comparison_shows_new_advanced_metrics():
    out = _capture_output(
        natural_query_run,
        query="Jokic vs Embiid recent form",
        pretty=True,
    )
    assert "USG%:" in out
    assert "AST%:" in out
    assert "REB%:" in out


def test_recent_form_player_comparison_v2_values_are_percent_scale():
    out = _capture_output(
        natural_query_run,
        query="Jokic vs Embiid recent form",
        pretty=True,
    )
    assert "USG%: 27." in out or "USG%: 28." in out or "USG%: 26." in out
    assert "AST%: 51." in out or "AST%: 50." in out or "AST%: 52." in out
    assert "REB%: 20." in out or "REB%: 19." in out or "REB%: 21." in out


def test_recent_form_explicit_last_n_team_summary_smoke():
    out = _capture_output(
        natural_query_run,
        query="Celtics last 15 games summary",
        pretty=True,
    )
    assert 'Query: "Celtics last 15 games summary"' in out
    assert "Boston Celtics" in out
    assert "Games: 15" in out
    assert "By Season" in out


def test_recent_form_playoff_default_smoke():
    out = _capture_output(
        natural_query_run,
        query="LeBron last 8 playoff games",
        pretty=True,
    )
    assert 'Query: "LeBron last 8 playoff games"' in out
    assert "Rows returned:" in out or "LeBron James" in out


def test_natural_player_split_pretty_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic home vs away in 2025-26",
        pretty=True,
    )
    assert 'Query: "Jokic home vs away in 2025-26"' in out
    assert "Nikola Jokić" in out
    assert "Split: Home vs Away" in out
    assert "Home vs Away" in out
    assert "Split Table" in out


def test_natural_player_split_shows_new_advanced_metrics():
    out = _capture_output(
        natural_query_run,
        query="Jokic home vs away in 2025-26",
        pretty=True,
    )
    assert "USG%:" in out
    assert "AST%:" in out
    assert "REB%:" in out


def test_natural_player_split_v2_metrics_differ_by_bucket():
    out = _capture_output(
        natural_query_run,
        query="Jokic home vs away in 2025-26",
        pretty=True,
    )
    assert "USG%: 30." in out or "USG%: 31." in out or "USG%: 29." in out
    assert "vs 29." in out or "vs 30." in out or "vs 28." in out
    assert "AST%: 52." in out or "AST%: 51." in out or "AST%: 53." in out
    assert "REB%: 20." in out or "REB%: 21." in out or "REB%: 19." in out


def test_natural_team_split_pretty_smoke():
    out = _capture_output(
        natural_query_run,
        query="Celtics wins vs losses",
        pretty=True,
    )
    assert 'Query: "Celtics wins vs losses"' in out
    assert "Boston Celtics" in out
    assert "Split: Wins vs Losses" in out
    assert "Wins vs Losses" in out
    assert "Split Table" in out


def test_natural_player_split_last_n_pretty_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic home away split last 20 games",
        pretty=True,
    )
    assert 'Query: "Jokic home away split last 20 games"' in out
    assert "Nikola Jokić" in out
    assert "Games: 20" in out
    assert "Split Table" in out


def test_single_threshold_player_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic last 10 games over 25 points",
        pretty=True,
    )
    assert 'Query: "Jokic last 10 games over 25 points"' in out
    assert "Rows returned:" in out
    assert "Nikola Jokić" in out


def test_single_threshold_team_smoke():
    out = _capture_output(
        natural_query_run,
        query="Celtics wins vs Bucks over 120 points",
        pretty=True,
    )
    assert 'Query: "Celtics wins vs Bucks over 120 points"' in out
    assert "Rows returned:" in out
    assert "Boston Celtics" in out or "team_name" in out


def test_multi_condition_player_and_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic last 10 games over 25 points and over 10 rebounds",
        pretty=True,
    )
    assert 'Query: "Jokic last 10 games over 25 points and over 10 rebounds"' in out
    assert "Rows returned:" in out
    assert "Nikola Jokić" in out


def test_multi_condition_team_and_smoke():
    out = _capture_output(
        natural_query_run,
        query="Celtics wins vs Bucks over 120 points and over 15 threes",
        pretty=True,
    )
    assert 'Query: "Celtics wins vs Bucks over 120 points and over 15 threes"' in out
    assert "Rows returned:" in out
    assert "Boston Celtics" in out or "team_name" in out


def test_under_query_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic under 20 points",
        pretty=True,
    )
    assert 'Query: "Jokic under 20 points"' in out
    assert "Rows returned:" in out
    assert "Nikola Jokić" in out


def test_between_query_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic between 20 and 30 points",
        pretty=True,
    )
    assert 'Query: "Jokic between 20 and 30 points"' in out
    assert "Rows returned:" in out
    assert "Nikola Jokić" in out


def test_mixed_over_and_under_query_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic last 10 games over 25 points and under 15 rebounds",
        pretty=True,
    )
    assert 'Query: "Jokic last 10 games over 25 points and under 15 rebounds"' in out
    assert "Rows returned:" in out
    assert "Nikola Jokić" in out


def test_or_query_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic over 25 points or over 10 rebounds",
        pretty=True,
    )
    assert 'Query: "Jokic over 25 points or over 10 rebounds"' in out
    assert "Rows returned:" in out
    assert "Nikola Jokić" in out
    assert " 40" in out or " 15" in out


def test_between_or_query_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic between 20 and 30 points or under 10 rebounds",
        pretty=True,
    )
    assert 'Query: "Jokic between 20 and 30 points or under 10 rebounds"' in out
    assert "Rows returned:" in out
    assert "Nikola Jokić" in out


def test_and_or_query_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic over 25 points and over 10 rebounds or over 15 assists",
        pretty=True,
    )
    assert 'Query: "Jokic over 25 points and over 10 rebounds or over 15 assists"' in out
    assert "Rows returned:" in out
    assert "Nikola Jokić" in out


def test_export_csv_creates_file(tmp_path):
    out_path = tmp_path / "jokic_and.csv"
    _capture_output(
        natural_query_run,
        query="Jokic last 10 games over 25 points and over 10 rebounds",
        pretty=True,
        export_csv_path=str(out_path),
    )
    assert out_path.exists()
    text = out_path.read_text(encoding="utf-8")
    assert "player_name" in text
    assert "Nikola Jokić" in text


def test_export_txt_creates_file(tmp_path):
    out_path = tmp_path / "jokic_embiid_recent.txt"
    _capture_output(
        natural_query_run,
        query="Jokic vs Embiid recent form",
        pretty=True,
        export_txt_path=str(out_path),
    )
    assert out_path.exists()
    text = out_path.read_text(encoding="utf-8")
    assert "Nikola Jokić vs Joel Embiid" in text
    assert "Comparison Table" in text


def test_export_json_tabular_creates_valid_json(tmp_path):
    out_path = tmp_path / "jokic_and.json"
    _capture_output(
        natural_query_run,
        query="Jokic last 10 games over 25 points and over 10 rebounds",
        pretty=True,
        export_json_path=str(out_path),
    )
    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert "metadata" in payload
    assert "finder" in payload
    assert isinstance(payload["finder"], list)
    assert len(payload["finder"]) >= 1
    assert payload["finder"][0]["player_name"] == "Nikola Jokić"


def test_export_json_summary_creates_structured_json(tmp_path):
    out_path = tmp_path / "jokic_embiid_recent.json"
    _capture_output(
        natural_query_run,
        query="Jokic vs Embiid recent form",
        pretty=True,
        export_json_path=str(out_path),
    )
    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert "summary" in payload
    assert "comparison" in payload
    assert payload["summary"][0]["player_name"] == "Nikola Jokić"


def test_structured_export_json_player_summary(tmp_path):
    out_path = tmp_path / "query_player_summary.json"
    out = _capture_output(
        _run_and_handle_exports,
        player_game_summary_run,
        season="2025-26",
        start_season=None,
        end_season=None,
        season_type="Regular Season",
        player="Nikola Jokić",
        team=None,
        opponent=None,
        home_only=False,
        away_only=False,
        wins_only=False,
        losses_only=False,
        stat=None,
        min_value=None,
        max_value=None,
        last_n=10,
        json_path=str(out_path),
    )
    assert "SUMMARY" in out
    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert "metadata" in payload
    assert "summary" in payload
    assert "by_season" in payload
    assert payload["summary"][0]["player_name"] == "Nikola Jokić"
    assert "usg_pct_avg" in payload["summary"][0]
    assert "ast_pct_avg" in payload["summary"][0]
    assert "reb_pct_avg" in payload["summary"][0]


def test_structured_export_txt_team_compare(tmp_path):
    out_path = tmp_path / "query_team_compare.txt"
    out = _capture_output(
        _run_and_handle_exports,
        team_compare_run,
        team_a="BOS",
        team_b="MIL",
        season=None,
        start_season="2021-22",
        end_season="2023-24",
        season_type="Regular Season",
        opponent=None,
        home_only=False,
        away_only=False,
        wins_only=False,
        losses_only=False,
        last_n=None,
        txt=str(out_path),
    )
    assert "METADATA" in out
    assert "SUMMARY" in out
    assert "COMPARISON" in out
    assert out_path.exists()
    text = out_path.read_text(encoding="utf-8")
    assert "METADATA" in text
    assert "SUMMARY" in text
    assert "COMPARISON" in text
    assert "BOS" in text
    assert "MIL" in text


def test_structured_export_csv_top_player_games(tmp_path):
    out_path = tmp_path / "top_player_games.csv"
    out = _capture_output(
        _run_and_handle_exports,
        top_player_games_run,
        "2005-06",
        "pts",
        5,
        "Regular Season",
        False,
        csv=str(out_path),
    )
    assert "player_name" in out
    assert out_path.exists()
    text = out_path.read_text(encoding="utf-8")
    assert "player_name" in text
    assert "Kobe Bryant" in text


def test_grouped_boolean_player_summary_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic summary (over 25 points and over 10 rebounds) or over 15 assists",
        pretty=True,
    )
    assert 'Query: "Jokic summary (over 25 points and over 10 rebounds) or over 15 assists"' in out
    assert "Nikola Jokić" in out
    assert "Games:" in out
    assert "Averages" in out
    assert "By Season" in out
    assert "USG%" in out
    assert "AST%" in out
    assert "REB%" in out


def test_grouped_boolean_player_split_summary_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic home vs away (over 25 points and over 10 rebounds) or over 15 assists",
        pretty=True,
    )
    assert (
        'Query: "Jokic home vs away (over 25 points and over 10 rebounds) or over 15 assists"'
        in out
    )
    assert "Nikola Jokić" in out
    assert "Split: Home vs Away" in out
    assert "Home vs Away" in out
    assert "Split Table" in out
    assert "USG%" in out
    assert "AST%" in out
    assert "REB%" in out


def test_grouped_boolean_team_summary_smoke():
    out = _capture_output(
        natural_query_run,
        query="Celtics summary (over 120 points and over 15 threes) or over 30 assists",
        pretty=True,
    )
    assert 'Query: "Celtics summary (over 120 points and over 15 threes) or over 30 assists"' in out
    assert "Boston Celtics" in out
    assert "Games:" in out
    assert "Averages" in out
    assert "By Season" in out
    assert "PTS" in out
    assert "3PM" in out
    assert "eFG%" in out
    assert "TS%" in out


def test_grouped_boolean_team_split_home_away_smoke():
    out = _capture_output(
        natural_query_run,
        query="Celtics home vs away (over 120 points and over 15 threes) or under 10 turnovers",
        pretty=True,
    )
    assert (
        'Query: "Celtics home vs away (over 120 points and over 15 threes) or under 10 turnovers"'
        in out
    )
    assert "Boston Celtics" in out
    assert "Split: Home vs Away" in out
    assert "Home vs Away" in out
    assert "Split Table" in out
    assert "3PM" in out
    assert "TOV" in out
    assert "eFG%" in out
    assert "TS%" in out


def test_grouped_boolean_team_split_wins_losses_smoke():
    out = _capture_output(
        natural_query_run,
        query="Celtics wins vs losses (over 120 points and over 15 threes) or under 10 turnovers",
        pretty=True,
    )
    assert (
        'Query: "Celtics wins vs losses (over 120 points and over 15 threes) or under 10 turnovers"'
        in out
    )
    assert "Boston Celtics" in out
    assert "Split: Wins vs Losses" in out
    assert "Wins vs Losses" in out
    assert "Split Table" in out
    assert "3PM" in out
    assert "TOV" in out
    assert "eFG%" in out
    assert "TS%" in out


# ---------------------------------------------------------------------------
# Structured CLI: result-contract scaffolding tests
# ---------------------------------------------------------------------------


def test_structured_cli_top_player_games_has_metadata_and_leaderboard():
    out = _capture_output(
        _run_and_handle_exports,
        top_player_games_run,
        "2005-06",
        "pts",
        5,
        "Regular Season",
        False,
    )
    sections = parse_labeled_sections(out)
    assert METADATA_LABEL in sections
    assert "LEADERBOARD" in sections
    meta = parse_metadata_block(sections[METADATA_LABEL])
    assert meta["route"] == "top_player_games"
    assert meta["query_class"] == "leaderboard"


def test_structured_cli_season_leaders_has_metadata_and_leaderboard():
    out = _capture_output(
        _run_and_handle_exports,
        season_leaders_run,
        season="2023-24",
        stat="ast",
        limit=5,
        season_type="Regular Season",
        min_games=20,
        ascending=False,
    )
    sections = parse_labeled_sections(out)
    assert METADATA_LABEL in sections
    assert "LEADERBOARD" in sections
    meta = parse_metadata_block(sections[METADATA_LABEL])
    assert meta["route"] == "season_leaders"
    assert meta["query_class"] == "leaderboard"
    assert meta["season"] == "2023-24"
    assert meta["season_type"] == "Regular Season"


def test_structured_cli_player_game_finder_has_metadata_and_finder():
    out = _capture_output(
        _run_and_handle_exports,
        player_game_finder_run,
        season="2005-06",
        start_season=None,
        end_season=None,
        season_type="Regular Season",
        player="Kobe Bryant",
        team=None,
        opponent="DAL",
        home_only=False,
        away_only=False,
        wins_only=False,
        losses_only=False,
        stat="pts",
        min_value=40,
        max_value=None,
        limit=25,
        sort_by="stat",
        ascending=False,
        last_n=None,
    )
    sections = parse_labeled_sections(out)
    assert METADATA_LABEL in sections
    assert "FINDER" in sections
    meta = parse_metadata_block(sections[METADATA_LABEL])
    assert meta["route"] == "player_game_finder"
    assert meta["query_class"] == "finder"
    assert meta["player"] == "Kobe Bryant"
    assert meta["opponent"] == "DAL"


def test_structured_cli_game_finder_has_metadata_and_finder():
    out = _capture_output(
        _run_and_handle_exports,
        game_finder_run,
        season=None,
        start_season="2021-22",
        end_season="2023-24",
        season_type="Regular Season",
        team="BOS",
        opponent="MIL",
        home_only=True,
        away_only=False,
        wins_only=True,
        losses_only=False,
        stat=None,
        min_value=None,
        max_value=None,
        limit=10,
        sort_by="game_date",
        ascending=False,
        last_n=None,
    )
    sections = parse_labeled_sections(out)
    assert METADATA_LABEL in sections
    assert "FINDER" in sections
    meta = parse_metadata_block(sections[METADATA_LABEL])
    assert meta["route"] == "game_finder"
    assert meta["query_class"] == "finder"
    assert meta["team"] == "BOS"
    assert meta["opponent"] == "MIL"
    assert meta["start_season"] == "2021-22"
    assert meta["end_season"] == "2023-24"


def test_structured_cli_player_summary_has_metadata_and_summary():
    out = _capture_output(
        _run_and_handle_exports,
        player_game_summary_run,
        season="2025-26",
        start_season=None,
        end_season=None,
        season_type="Regular Season",
        player="Nikola Jokić",
        team=None,
        opponent=None,
        home_only=False,
        away_only=False,
        wins_only=False,
        losses_only=False,
        stat=None,
        min_value=None,
        max_value=None,
        last_n=10,
    )
    sections = parse_labeled_sections(out)
    assert METADATA_LABEL in sections
    assert "SUMMARY" in sections
    assert "BY_SEASON" in sections
    meta = parse_metadata_block(sections[METADATA_LABEL])
    assert meta["route"] == "player_game_summary"
    assert meta["query_class"] == "summary"
    assert meta["player"] == "Nikola Jokić"


def test_structured_cli_team_compare_has_metadata_and_comparison():
    out = _capture_output(
        _run_and_handle_exports,
        team_compare_run,
        team_a="BOS",
        team_b="MIL",
        season=None,
        start_season="2021-22",
        end_season="2023-24",
        season_type="Regular Season",
        opponent=None,
        home_only=False,
        away_only=False,
        wins_only=False,
        losses_only=False,
        last_n=None,
    )
    sections = parse_labeled_sections(out)
    assert METADATA_LABEL in sections
    assert "SUMMARY" in sections
    assert "COMPARISON" in sections
    meta = parse_metadata_block(sections[METADATA_LABEL])
    assert meta["route"] == "team_compare"
    assert meta["query_class"] == "comparison"
    assert meta["team"] == "BOS, MIL"


def test_structured_cli_player_split_has_metadata_and_split():
    out = _capture_output(
        _run_and_handle_exports,
        player_split_summary_run,
        split="home_away",
        season="2025-26",
        start_season=None,
        end_season=None,
        season_type="Regular Season",
        player="Nikola Jokić",
        team=None,
        opponent=None,
        stat=None,
        min_value=None,
        max_value=None,
        last_n=None,
    )
    sections = parse_labeled_sections(out)
    assert METADATA_LABEL in sections
    assert "SUMMARY" in sections
    assert "SPLIT_COMPARISON" in sections
    meta = parse_metadata_block(sections[METADATA_LABEL])
    assert meta["route"] == "player_split_summary"
    assert meta["query_class"] == "split_summary"
    assert meta["split_type"] == "home_away"


def test_structured_cli_player_streak_has_metadata_and_streak():
    out = _capture_output(
        _run_and_handle_exports,
        player_streak_finder_run,
        season="2025-26",
        start_season=None,
        end_season=None,
        season_type="Regular Season",
        player="Nikola Jokić",
        team=None,
        opponent=None,
        home_only=False,
        away_only=False,
        wins_only=False,
        losses_only=False,
        start_date=None,
        end_date=None,
        last_n=None,
        stat="pts",
        min_value=20,
        max_value=None,
        special_condition=None,
        min_streak_length=3,
        longest=False,
        limit=25,
    )
    sections = parse_labeled_sections(out)
    assert METADATA_LABEL in sections
    assert "STREAK" in sections
    meta = parse_metadata_block(sections[METADATA_LABEL])
    assert meta["route"] == "player_streak_finder"
    assert meta["query_class"] == "streak"
    assert meta["player"] == "Nikola Jokić"


def test_structured_cli_json_export_has_metadata(tmp_path):
    out_path = tmp_path / "cli_summary.json"
    _capture_output(
        _run_and_handle_exports,
        player_game_summary_run,
        season="2025-26",
        start_season=None,
        end_season=None,
        season_type="Regular Season",
        player="Nikola Jokić",
        team=None,
        opponent=None,
        home_only=False,
        away_only=False,
        wins_only=False,
        losses_only=False,
        stat=None,
        min_value=None,
        max_value=None,
        last_n=10,
        json_path=str(out_path),
    )
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert "metadata" in payload
    assert "summary" in payload
    assert "by_season" in payload
    assert payload["metadata"]["route"] == "player_game_summary"
    assert payload["metadata"]["query_class"] == "summary"


def test_structured_cli_csv_export_strips_metadata(tmp_path):
    out_path = tmp_path / "cli_top.csv"
    _capture_output(
        _run_and_handle_exports,
        top_player_games_run,
        "2005-06",
        "pts",
        5,
        "Regular Season",
        False,
        csv=str(out_path),
    )
    text = out_path.read_text(encoding="utf-8")
    assert "METADATA" not in text
    assert "LEADERBOARD" not in text
    assert "player_name" in text
    assert "Kobe Bryant" in text


def test_structured_cli_txt_export_has_metadata(tmp_path):
    out_path = tmp_path / "cli_compare.txt"
    _capture_output(
        _run_and_handle_exports,
        team_compare_run,
        team_a="BOS",
        team_b="MIL",
        season=None,
        start_season="2021-22",
        end_season="2023-24",
        season_type="Regular Season",
        opponent=None,
        home_only=False,
        away_only=False,
        wins_only=False,
        losses_only=False,
        last_n=None,
        txt=str(out_path),
    )
    text = out_path.read_text(encoding="utf-8")
    assert "METADATA" in text
    assert "SUMMARY" in text
    assert "COMPARISON" in text
    assert "BOS" in text
    assert "MIL" in text
