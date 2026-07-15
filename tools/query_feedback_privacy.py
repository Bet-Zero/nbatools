# ruff: noqa: E402, I001

"""Read-only lifecycle verification and explicit feedback deletion commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nbatools.data_source import create_r2_client  # noqa: E402
from nbatools.query_feedback import (  # noqa: E402
    DEFAULT_QUERY_FEEDBACK_PREFIX,
    QUERY_FEEDBACK_BUCKET_ENV,
    load_feedback_r2_config,
)
from nbatools.query_feedback_privacy import (  # noqa: E402
    delete_feedback_by_receipt,
    verify_feedback_lifecycle,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", default=None)
    parser.add_argument("--prefix", default=DEFAULT_QUERY_FEEDBACK_PREFIX)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "verify-lifecycle",
        help="Read and verify the configured lifecycle without mutating it.",
    )
    delete = subparsers.add_parser(
        "delete-receipt",
        help="Delete and verify one UUID-backed feedback receipt.",
    )
    delete.add_argument("feedback_id")
    delete.add_argument(
        "--confirm-feedback-id",
        required=True,
        help="Repeat the exact feedback ID to authorize the destructive operation.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_feedback_r2_config(bucket_name=args.bucket)
    bucket_name = args.bucket or config.bucket_name
    if not bucket_name:
        raise ValueError(f"Set --bucket or {QUERY_FEEDBACK_BUCKET_ENV}")
    client = create_r2_client(config)

    if args.command == "verify-lifecycle":
        result = verify_feedback_lifecycle(
            client,
            bucket_name=bucket_name,
            prefix=args.prefix,
        )
        print(json.dumps(result.__dict__, sort_keys=True))
        return 0

    if args.feedback_id != args.confirm_feedback_id:
        raise ValueError("--confirm-feedback-id must exactly match feedback_id")
    receipt = delete_feedback_by_receipt(
        client,
        bucket_name=bucket_name,
        prefix=args.prefix,
        feedback_id=args.feedback_id,
    )
    print(json.dumps(receipt.as_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
