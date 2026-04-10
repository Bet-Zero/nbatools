from nbatools.commands._seasons import int_to_season, season_to_int
from nbatools.commands.backfill_season import run as backfill_season_run


def run(start_season: str, end_season: str, include_playoffs: bool, skip_existing: bool = False):
    start = season_to_int(start_season)
    end = season_to_int(end_season)

    for year in range(start, end + 1):
        season = int_to_season(year)

        print("\n==============================")
        print(f"BACKFILLING {season} REGULAR SEASON")
        print("==============================")

        backfill_season_run(season, "Regular Season", skip_existing)

        if include_playoffs:
            print("\n==============================")
            print(f"BACKFILLING {season} PLAYOFFS")
            print("==============================")

            backfill_season_run(season, "Playoffs", skip_existing)
