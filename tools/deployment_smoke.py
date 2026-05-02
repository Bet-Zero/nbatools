from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from nbatools.deployment_monitoring import run_deployment_smoke


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run deployment smoke checks against a deployed nbatools base URL."
    )
    parser.add_argument("--base-url", required=True, help="Deployment base URL to probe")
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Per-request timeout in seconds (default: 20)",
    )
    parser.add_argument(
        "--output",
        help="Optional JSON output path. Defaults to stdout only when omitted.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run_deployment_smoke(args.base_url, timeout=args.timeout)
    rendered = json.dumps(report.to_dict(), indent=2)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n")

    print(rendered)
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
