"""Helpers for monitoring deployed nbatools environments."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from urllib import request

INTERESTING_HEADERS = (
    "server",
    "cache-control",
    "content-type",
    "content-length",
    "x-vercel-cache",
    "x-vercel-id",
)


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "checked_at": self.checked_at,
            "ok": self.ok,
            "case_count": self.case_count,
            "failure_count": self.failure_count,
            "failures": self.failures,
            "cases": [asdict(case) for case in self.cases],
        }


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
    ]


def fetch_http(url: str, method: str, body: dict[str, Any] | None, timeout: float) -> FetchResponse:
    headers: dict[str, str] = {}
    data: bytes | None = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")

    req = request.Request(url, data=data, headers=headers, method=method)
    with request.urlopen(req, timeout=timeout) as response:
        return response.status, dict(response.headers.items()), response.read()


def run_deployment_smoke(
    base_url: str,
    *,
    cases: list[SmokeCase] | None = None,
    timeout: float = 20.0,
    fetcher: Fetcher = fetch_http,
) -> SmokeReport:
    normalized_base_url = normalize_base_url(base_url)
    results: list[SmokeCaseResult] = []
    failures: list[str] = []

    for case in cases or default_smoke_cases():
        url = normalized_base_url + case.path
        started = perf_counter()
        try:
            status, headers, body = fetcher(url, case.method, case.body, timeout)
            duration_ms = round((perf_counter() - started) * 1000, 3)
            result = _evaluate_case(case, url, status, headers, body, duration_ms)
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
    )


def _evaluate_case(
    case: SmokeCase,
    url: str,
    status: int,
    headers: Mapping[str, str],
    body: bytes,
    duration_ms: float,
) -> SmokeCaseResult:
    lowered_headers = {str(key).lower(): str(value) for key, value in headers.items()}
    selected_headers = {
        key: lowered_headers[key] for key in INTERESTING_HEADERS if key in lowered_headers
    }

    decoded = body.decode("utf-8", errors="replace")
    payload = _parse_json(decoded, lowered_headers)
    summary = _summarize_payload(case.slug, decoded, payload)

    error: str | None = None
    if status != case.expected_status:
        error = f"expected HTTP {case.expected_status}, got {status}"
    elif case.required_text:
        missing = [snippet for snippet in case.required_text if snippet not in decoded]
        if missing:
            error = f"missing expected text: {', '.join(missing)}"
    if error is None and case.forbidden_text:
        forbidden = [snippet for snippet in case.forbidden_text if snippet in decoded]
        if forbidden:
            error = f"found forbidden text: {', '.join(forbidden)}"
    if error is None and case.expected_json_fields:
        if not isinstance(payload, dict):
            error = "expected JSON body but response was not JSON"
        else:
            mismatches = []
            for key, expected in case.expected_json_fields.items():
                actual = payload.get(key)
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
        body_preview=decoded[:240],
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
    )
    summary = {key: payload[key] for key in fields if key in payload}
    if slug == "freshness" and isinstance(payload.get("seasons"), list):
        summary["season_count"] = len(payload["seasons"])
    return summary
