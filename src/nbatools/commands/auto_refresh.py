"""Local automation runner for current-season data refreshes.

Provides a durable loop that periodically invokes the pipeline refresh
workflow, logs outcomes, and can be stopped cleanly with Ctrl-C or
SIGTERM.  Designed for local-first usage — no cloud infra required.

Usage (via CLI)::

    nbatools-cli pipeline auto-refresh --interval 6h
    nbatools-cli pipeline auto-refresh --interval 30m --include-playoffs

The runner:
1. Executes ``refresh_current_season()`` immediately on start.
2. Sleeps for *interval* between runs.
3. Writes a ``last_refresh.json`` log after each attempt.
4. Prints a summary line after each refresh.
5. Exits cleanly on keyboard interrupt or signal.
"""

from __future__ import annotations

import signal
import time
from datetime import datetime

from nbatools.commands.freshness import write_refresh_log
from nbatools.commands.pipeline import PipelineResult, refresh_current_season


def _format_interval(seconds: int) -> str:
    """Human-readable interval string."""
    if seconds >= 3600:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h{m}m" if m else f"{h}h"
    if seconds >= 60:
        return f"{seconds // 60}m"
    return f"{seconds}s"


def parse_interval(text: str) -> int:
    """Parse a human-friendly interval like '6h', '30m', '90s' to seconds.

    Supports:
    - ``6h`` / ``6H`` → 21600
    - ``30m`` / ``30M`` → 1800
    - ``90s`` / ``90S`` → 90
    - ``3600`` (plain int) → 3600

    Raises ValueError on invalid input.
    """
    text = text.strip()
    if not text:
        raise ValueError("Empty interval string")

    suffix = text[-1].lower()
    if suffix == "h":
        return int(text[:-1]) * 3600
    if suffix == "m":
        return int(text[:-1]) * 60
    if suffix == "s":
        return int(text[:-1])
    # Assume seconds if purely numeric
    return int(text)


def _log_result(result: PipelineResult) -> None:
    """Write refresh log and print summary."""
    ts = result.finished_at or datetime.now().isoformat(timespec="seconds")
    if result.success:
        write_refresh_log(success=True, timestamp=ts)
        ct_parts = []
        for sr in result.seasons:
            if sr.current_through:
                ct_parts.append(f"{sr.season}: {sr.current_through}")
        ct_str = ", ".join(ct_parts) if ct_parts else "(no current_through)"
        print(f"[{ts}] ✅ Refresh succeeded — {ct_str}")
    else:
        errors = []
        for sr in result.failed_seasons:
            for st in sr.failed_stages:
                errors.append(f"{sr.season}/{st.name}: {st.error}")
        error_summary = "; ".join(errors) if errors else "unknown error"
        write_refresh_log(success=False, timestamp=ts, error=error_summary)
        print(f"[{ts}] ❌ Refresh failed — {error_summary}")


def run_auto_refresh(
    interval_seconds: int,
    *,
    include_playoffs: bool = False,
    max_iterations: int | None = None,
) -> None:
    """Run the refresh loop until interrupted.

    Parameters
    ----------
    interval_seconds : int
        Seconds between refresh cycles.
    include_playoffs : bool
        Also refresh playoff data each cycle.
    max_iterations : int | None
        If set, exit after this many iterations (useful for testing).
    """
    stop = False

    def _handle_signal(signum, frame):  # noqa: ARG001
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    interval_label = _format_interval(interval_seconds)
    print(f"Auto-refresh starting — interval: {interval_label}, playoffs: {include_playoffs}")
    print("Press Ctrl-C to stop.\n")

    iteration = 0
    while not stop:
        iteration += 1
        if max_iterations is not None and iteration > max_iterations:
            break

        print(f"[{datetime.now().isoformat(timespec='seconds')}] Starting refresh #{iteration}…")
        try:
            result = refresh_current_season(include_playoffs=include_playoffs)
            _log_result(result)
        except Exception as exc:
            ts = datetime.now().isoformat(timespec="seconds")
            write_refresh_log(success=False, timestamp=ts, error=str(exc))
            print(f"[{ts}] ❌ Refresh crashed — {exc}")

        if stop:
            break
        if max_iterations is not None and iteration >= max_iterations:
            break

        # Interruptible sleep
        deadline = time.monotonic() + interval_seconds
        while time.monotonic() < deadline and not stop:
            time.sleep(min(1.0, deadline - time.monotonic()))

    print("\nAuto-refresh stopped.")
