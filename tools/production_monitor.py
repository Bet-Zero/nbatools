"""Run the policy-bound production monitor or its notification-delivery test."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from nbatools.production_monitoring import (
    run_production_monitor,
    synthetic_notification_failure,
)
from nbatools.production_publication_evidence import (
    GitHubPublicationEvidence,
    PublicationEvidenceError,
    resolve_verified_publication,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the nbatools production monitor.")
    parser.add_argument("--base-url", help="Public production base URL")
    generation = parser.add_mutually_exclusive_group()
    generation.add_argument(
        "--expected-generation", help="Expected immutable production generation"
    )
    generation.add_argument(
        "--expected-verified-publication",
        action="store_true",
        help="Resolve the expected generation from the repository's verified publication",
    )
    parser.add_argument("--output", help="Optional JSON receipt path")
    parser.add_argument(
        "--synthetic-failure",
        action="store_true",
        help="Fail without network access to prove notification delivery",
    )
    return parser


def _probe(args):
    expected = args.expected_generation
    publication = None
    if args.expected_verified_publication:
        try:
            publication = resolve_verified_publication(
                GitHubPublicationEvidence(os.getenv("GH_TOKEN"))
            )
        except PublicationEvidenceError as exc:
            return {
                "schema_version": 1,
                "kind": "production_monitor",
                "checked_at": datetime.now(UTC).isoformat(),
                "ok": False,
                "notification_required": True,
                "failure_count": 1,
                "failures": ["verified_publication_resolution"],
                "error": str(exc),
                "expected_generation": None,
                "snapshot_status": "not_checked",
                "live_readiness": "not_checked",
                "cases": [],
            }
        expected = publication.generation_id
    report = run_production_monitor(args.base_url, expected_generation=expected).to_dict()
    if publication:
        report["verified_publication"] = asdict(publication)
    return report


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.synthetic_failure and not args.base_url:
        parser.error("--base-url is required unless --synthetic-failure is used")
    payload = synthetic_notification_failure() if args.synthetic_failure else _probe(args)

    rendered = json.dumps(payload, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
