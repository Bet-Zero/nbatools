from __future__ import annotations

import subprocess
import sys


def run(verbose: bool = False) -> None:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_natural_query_parser.py",
        "tests/test_cli_smoke.py",
    ]

    if not verbose:
        cmd.append("-q")

    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
