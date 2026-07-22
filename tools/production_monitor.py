"""Run the policy-bound production monitor or its notification-delivery test."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from nbatools.production_monitoring import (
    run_production_monitor,
    synthetic_notification_failure,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the nbatools production monitor.")
    parser.add_argument("--base-url", help="Public production base URL")
    parser.add_argument("--output", help="Optional JSON receipt path")
    parser.add_argument(
        "--synthetic-failure",
        action="store_true",
        help="Fail without network access to prove notification delivery",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.synthetic_failure:
        payload = synthetic_notification_failure()
    else:
        if not args.base_url:
            build_parser().error("--base-url is required unless --synthetic-failure is used")
        payload = run_production_monitor(args.base_url).to_dict()

    rendered = json.dumps(payload, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
