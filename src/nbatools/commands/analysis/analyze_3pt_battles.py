from pathlib import Path

import pandas as pd


def run(season: str, season_type: str) -> None:
    safe_season_type = season_type.lower().replace(" ", "_")
    in_path = Path(f"data/raw/team_game_stats/{season}_{safe_season_type}.csv")

    if not in_path.exists():
        raise FileNotFoundError(f"Missing required input file: {in_path}")

    df = pd.read_csv(in_path)

    required = [
        "game_id",
        "team_id",
        "wl",
        "fg3m",
        "fg3_pct",
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    made_win = 0
    made_loss = 0
    made_tie = 0

    pct_win = 0
    pct_loss = 0
    pct_tie = 0

    processed_games = 0
    skipped_games = 0

    for game_id, game in df.groupby("game_id"):
        if len(game) != 2:
            skipped_games += 1
            continue

        rows = game.reset_index(drop=True)
        a = rows.iloc[0]
        b = rows.iloc[1]

        if a["wl"] == "W":
            winner = "A"
        elif b["wl"] == "W":
            winner = "B"
        else:
            skipped_games += 1
            continue

        processed_games += 1

        # 3PM battle
        if a["fg3m"] > b["fg3m"]:
            made_battle = "A"
        elif b["fg3m"] > a["fg3m"]:
            made_battle = "B"
        else:
            made_battle = "TIE"

        if made_battle == "TIE":
            made_tie += 1
        elif made_battle == winner:
            made_win += 1
        else:
            made_loss += 1

        # 3PT% battle
        if a["fg3_pct"] > b["fg3_pct"]:
            pct_battle = "A"
        elif b["fg3_pct"] > a["fg3_pct"]:
            pct_battle = "B"
        else:
            pct_battle = "TIE"

        if pct_battle == "TIE":
            pct_tie += 1
        elif pct_battle == winner:
            pct_win += 1
        else:
            pct_loss += 1

    def pct_str(wins: int, losses: int) -> str:
        total = wins + losses
        if total == 0:
            return "0.0%"
        return f"{(wins / total) * 100:.1f}%"

    print()
    print(f"NBA 3PT Battle Analysis — {season} {season_type}")
    print("-" * 50)
    print(f"Processed games: {processed_games}")
    if skipped_games:
        print(f"Skipped games:   {skipped_games}")

    print()
    print("More 3PM won:")
    print(f"  {made_win}-{made_loss} ({pct_str(made_win, made_loss)})")
    print(f"  Ties: {made_tie}")

    print()
    print("Better 3PT% won:")
    print(f"  {pct_win}-{pct_loss} ({pct_str(pct_win, pct_loss)})")
    print(f"  Ties: {pct_tie}")
    print()
