from pathlib import Path

import pandas as pd


def run() -> None:
    path = Path("data/metadata/backfill_manifest.csv")
    if not path.exists():
        print("No manifest found.")
        return

    df = pd.read_csv(path)
    print(df.to_csv(index=False))
