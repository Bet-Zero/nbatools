"""Helpers for monitoring deployed nbatools environments."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from urllib import request
from urllib.error import HTTPError

from nbatools.api_ui import UI_FALLBACK_ASSET

INTERESTING_HEADERS = (
    "server",
    "cache-control",
    "content-type",
    "content-length",
    "x-vercel-cache",
    "x-vercel-id",
    "x-request-id",
)
MAX_SMOKE_RESPONSE_BYTES = 1_048_576
_SNAPSHOT_GENERATION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


class ResponseTooLargeError(RuntimeError):
    """Raised when a smoke endpoint exceeds the bounded response budget."""


@dataclass(frozen=True)
class SmokeCase:
    slug: str
    path: str
    method: str = "GET"
    body: dict[str, Any] | None = None
    expected_status: int = 200
    expected_json_fields: dict[str, Any] = field(default_factory=dict)
    required_text: tuple[str, ...] = ()
    forbidden_text: tuple[str, ...] = ()


@dataclass(frozen=True)
class SmokeCaseResult:
    slug: str
    method: str
    url: str
    ok: bool
    status_code: int | None
    duration_ms: float
    headers: dict[str, str]
    summary: dict[str, Any]
    error: str | None = None
    body_preview: str | None = None


@dataclass(frozen=True)
class SmokeReport:
    base_url: str
    checked_at: str
    ok: bool
    case_count: int
    failure_count: int
    failures: list[str]
    cases: list[SmokeCaseResult]
    snapshot_generation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        report = {
            "base_url": self.base_url,
            "checked_at": self.checked_at,
            "ok": self.ok,
            "case_count": self.case_count,
            "failure_count": self.failure_count,
            "failures": self.failures,
            "cases": [asdict(case) for case in self.cases],
        }
        if self.snapshot_generation is not None:
            report["scope"] = "snapshot_recovery"
            report["expected_generation"] = self.snapshot_generation
        return report


FetchResponse = tuple[int, Mapping[str, str], bytes]
Fetcher = Callable[[str, str, dict[str, Any] | None, float], FetchResponse]


def normalize_base_url(base_url: str) -> str:
    cleaned = str(base_url or "").strip()
    if not cleaned:
        raise ValueError("base_url must be a non-empty URL")
    return cleaned.rstrip("/")


def default_smoke_cases() -> list[SmokeCase]:
    return [
        SmokeCase(
            slug="root",
            path="/",
            forbidden_text=("nbatools UI bundle not built",),
        ),
        SmokeCase(
            slug="health",
            path="/health",
            expected_json_fields={"status": "ok"},
        ),
        SmokeCase(
            slug="freshness",
            path="/freshness",
        ),
        SmokeCase(
            slug="readiness",
            path="/readiness",
            expected_json_fields={"ready": True, "status": "ready"},
        ),
        SmokeCase(
            slug="query_jokic_last_10",
            path="/query",
            method="POST",
            body={"query": "Jokic last 10"},
            expected_json_fields={"ok": True, "route": "player_game_summary"},
        ),
        SmokeCase(
            slug="query_top_10_scorers_2025_26",
            path="/query",
            method="POST",
            body={"query": "top 10 scorers 2025-26"},
            expected_json_fields={"ok": True, "route": "season_leaders"},
        ),
        SmokeCase(
            slug="query_jokic_multi_filter",
            path="/query",
            method="POST",
            body={"query": "Jokic summary (over 25 points and over 10 rebounds) 2025-26"},
            expected_json_fields={"ok": True, "route": "player_game_summary"},
        ),
        SmokeCase(
            slug="query_celtics_record_against_east_current",
            path="/query",
            method="POST",
            body={"query": "Celtics record against the East this season"},
            expected_json_fields={
                "ok": True,
                "route": "team_record",
                "result_status": "ok",
                "result.metadata.opponent_conference": "East",
                "result.metadata.opponent_team_abbrs.__len__": 15,
            },
        ),
    ]


def _snapshot_recovery_smoke_cases() -> list[SmokeCase]:
    cases = []
    for case in default_smoke_cases():
        if case.slug == "root":
            case = replace(
                case,
                required_text=("/assets/",),
                forbidden_text=(*case.forbidden_text, UI_FALLBACK_ASSET),
            )
        if case.slug == "query_celtics_record_against_east_current":
            case = replace(
                case,
                slug="query_celtics_record_against_east_2025_26",
                body={"query": "Celtics record against the East in 2025-26"},
                expected_json_fields={
                    **case.expected_json_fields,
                    "result.metadata.team": "BOS",
                    "result.metadata.season": "2025-26",
                },
            )
        if case.method == "POST":
            case = replace(
                case, expected_json_fields={**case.expected_json_fields, "result_status": "ok"}
            )
        cases.append(case)
    return cases


def fetch_http(url: str, method: str, body: dict[str, Any] | None, timeout: float) -> FetchResponse:
    headers: dict[str, str] = {}
    data: bytes | None = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")

    req = request.Request(url, data=data, headers=headers, method=method)
    with request.urlopen(req, timeout=timeout) as response:
        return _read_http_response(response)


def _read_http_response(response: Any) -> FetchResponse:
    body = response.read(MAX_SMOKE_RESPONSE_BYTES + 1)
    if len(body) > MAX_SMOKE_RESPONSE_BYTES:
        raise ResponseTooLargeError("response exceeded the safe smoke-monitoring limit")
    headers = dict(response.headers.items()) if response.headers is not None else {}
    return response.status, headers, body


def run_deployment_smoke(
    base_url: str,
    *,
    cases: list[SmokeCase] | None = None,
    snapshot_generation: str | None = None,
    timeout: float = 20.0,
    fetcher: Fetcher = fetch_http,
) -> SmokeReport:
    normalized_base_url = normalize_base_url(base_url)
    results: list[SmokeCaseResult] = []
    failures: list[str] = []
    if snapshot_generation is not None:
        if not _SNAPSHOT_GENERATION.fullmatch(snapshot_generation):
            raise ValueError("snapshot generation must be a safe immutable generation ID")
        if cases is not None:
            raise ValueError("snapshot recovery uses the registered smoke cases")
        cases = _snapshot_recovery_smoke_cases()

    for case in cases or default_smoke_cases():
        url = normalized_base_url + case.path
        started = perf_counter()
        try:
            try:
                status, headers, body = fetcher(url, case.method, case.body, timeout)
            except HTTPError as exc:
                if snapshot_generation is None or case.slug != "readiness" or exc.code != 503:
                    raise
                with exc:
                    status, headers, body = _read_http_response(exc)
            duration_ms = round((perf_counter() - started) * 1000, 3)
            result = evaluate_smoke_response(
                case,
                url,
                status,
                headers,
                body,
                duration_ms,
                snapshot_generation=snapshot_generation,
            )
        except Exception as exc:
            duration_ms = round((perf_counter() - started) * 1000, 3)
            result = SmokeCaseResult(
                slug=case.slug,
                method=case.method,
                url=url,
                ok=False,
                status_code=None,
                duration_ms=duration_ms,
                headers={},
                summary={},
                error=f"{type(exc).__name__}: {exc}",
            )

        if not result.ok:
            failures.append(result.slug)
        results.append(result)

    checked_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return SmokeReport(
        base_url=normalized_base_url,
        checked_at=checked_at,
        ok=not failures,
        case_count=len(results),
        failure_count=len(failures),
        failures=failures,
        cases=results,
        snapshot_generation=snapshot_generation,
    )


def evaluate_smoke_response(
    case: SmokeCase,
    url: str,
    status: int,
    headers: Mapping[str, str],
    body: bytes,
    duration_ms: float,
    *,
    snapshot_generation: str | None = None,
) -> SmokeCaseResult:
    lowered_headers = {str(key).lower(): str(value) for key, value in headers.items()}
    selected_headers = {
        key: lowered_headers[key] for key in INTERESTING_HEADERS if key in lowered_headers
    }

    snapshot_readiness = snapshot_generation is not None and case.slug == "readiness"
    try:
        decoded = body.decode("utf-8", errors="strict" if snapshot_readiness else "replace")
    except UnicodeDecodeError:
        decoded = ""
    payload = _parse_json(decoded, lowered_headers)
    summary = _summarize_payload(case.slug, decoded, payload)

    error: str | None = None
    if snapshot_readiness:
        known_live_gap = (
            status == 503
            and isinstance(payload, dict)
            and snapshot_live_gap_matches(payload, snapshot_generation)
        )
        ready = (
            status == 200
            and isinstance(payload, dict)
            and payload.get("ready") is True
            and payload.get("status") == "ready"
            and payload.get("immutable_generation") is True
            and payload.get("active_generation") == snapshot_generation
            and payload.get("blockers") == []
        )
        if known_live_gap or ready:
            summary["live_readiness"] = "known_live_gap" if known_live_gap else "passed"
        else:
            summary = {}
            error = "snapshot readiness confirmation failed"
    elif status != case.expected_status:
        error = f"expected HTTP {case.expected_status}, got {status}"
    elif case.required_text:
        missing = [snippet for snippet in case.required_text if snippet not in decoded]
        if missing:
            error = f"missing expected text: {', '.join(missing)}"
    if error is None and case.forbidden_text:
        forbidden = [snippet for snippet in case.forbidden_text if snippet in decoded]
        if forbidden:
            error = f"found forbidden text: {', '.join(forbidden)}"
    if error is None and case.expected_json_fields and not snapshot_readiness:
        if not isinstance(payload, dict):
            error = "expected JSON body but response was not JSON"
        else:
            mismatches = []
            for key, expected in case.expected_json_fields.items():
                actual = _json_path_value(payload, key)
                if actual != expected:
                    mismatches.append(f"{key}={actual!r} (expected {expected!r})")
            if mismatches:
                error = "; ".join(mismatches)

    return SmokeCaseResult(
        slug=case.slug,
        method=case.method,
        url=url,
        ok=error is None,
        status_code=status,
        duration_ms=duration_ms,
        headers=selected_headers,
        summary=summary,
        error=error,
        body_preview=None if snapshot_readiness else decoded[:240],
    )


def _parse_json(decoded: str, headers: Mapping[str, str]) -> dict[str, Any] | list[Any] | None:
    content_type = headers.get("content-type", "")
    looks_like_json = decoded.lstrip().startswith(("{", "["))
    if "json" not in content_type and not looks_like_json:
        return None
    try:
        return json.loads(decoded)
    except json.JSONDecodeError:
        return None


def _json_path_value(payload: Mapping[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if part == "__len__":
            if isinstance(current, Sequence) and not isinstance(current, str | bytes | bytearray):
                current = len(current)
                continue
            return None
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return current


def _summarize_payload(
    slug: str,
    decoded: str,
    payload: dict[str, Any] | list[Any] | None,
) -> dict[str, Any]:
    if slug == "root":
        title_match = re.search(r"<title>(.*?)</title>", decoded, flags=re.IGNORECASE | re.DOTALL)
        return {
            "title": title_match.group(1).strip() if title_match else None,
            "fallback_shell_detected": "nbatools UI bundle not built" in decoded,
            "contains_assets_reference": "/assets/" in decoded,
        }

    if not isinstance(payload, dict):
        return {}

    fields = (
        "status",
        "version",
        "current_through",
        "checked_at",
        "last_refresh_ok",
        "ok",
        "route",
        "query_class",
        "result_status",
        "confidence",
        "ready",
        "season_state",
        "active_generation",
        "immutable_generation",
    )
    summary = {key: payload[key] for key in fields if key in payload}
    if slug == "freshness" and isinstance(payload.get("seasons"), list):
        summary["season_count"] = len(payload["seasons"])
    if slug == "readiness" and isinstance(payload.get("blockers"), list):
        summary["blocker_count"] = len(payload["blockers"])
    result = payload.get("result")
    if isinstance(result, dict):
        metadata = result.get("metadata")
        if isinstance(metadata, dict):
            if metadata.get("opponent_conference"):
                summary["opponent_conference"] = metadata["opponent_conference"]
            opponent_team_abbrs = metadata.get("opponent_team_abbrs")
            if isinstance(opponent_team_abbrs, list):
                summary["opponent_team_abbrs_count"] = len(opponent_team_abbrs)
    return summary


def snapshot_live_gap_matches(payload: dict[str, Any], expected_generation: str | None) -> bool:
    """Match the native readiness response before reducing it for safe logging."""
    if (
        expected_generation is None
        or payload.get("active_generation") != expected_generation
        or payload.get("immutable_generation") is not True
        or payload.get("ready") is not False
        or payload.get("status") != "not_ready"
        or not all(
            isinstance(payload.get(key), str) and payload[key]
            for key in (
                "checked_at",
                "season",
                "season_state",
                "release_exception_owner",
            )
        )
        or type(payload.get("max_active_lag_hours")) is not int
        or not isinstance(payload.get("slices"), list)
        or not payload["slices"]
        or not all(_has_slice_schema(row) for row in payload["slices"])
    ):
        return False

    exception = payload.get("exception")
    if (
        not isinstance(exception, dict)
        or exception.get("applied") is not False
        or exception.keys() != {"applied", "owner", "reason", "created_at", "expires_at", "error"}
        or not isinstance(exception["owner"], str)
        or any(
            exception[key] is not None for key in ("reason", "created_at", "expires_at", "error")
        )
    ):
        return False

    blockers = payload.get("blockers")
    if not isinstance(blockers, list) or len(blockers) != 1:
        return False
    blocker = blockers[0]
    return (
        isinstance(blocker, dict)
        and blocker.keys() == {"code", "detail"}
        and blocker["code"] == "new_season_not_loaded"
        and isinstance(blocker["detail"], str)
        and bool(blocker["detail"].strip())
    )


def _has_slice_schema(row: Any) -> bool:
    if not isinstance(row, dict):
        return False
    return (
        all(isinstance(row.get(key), str) for key in ("season", "season_type", "validation_state"))
        and all(
            type(row.get(key)) is bool
            for key in (
                "trusted",
                "schedule_complete",
                "postseason_complete",
            )
        )
        and all(
            key in row and (row[key] is None or isinstance(row[key], str))
            for key in ("generation_id", "current_through", "expected_current_through")
        )
        and isinstance(row.get("errors"), list)
        and all(isinstance(error, str) for error in row["errors"])
        and "missing_due_game_ids" in row
        and (
            row["missing_due_game_ids"] is None
            or (
                isinstance(row["missing_due_game_ids"], list)
                and all(isinstance(game_id, str) for game_id in row["missing_due_game_ids"])
            )
        )
    )
