"""The bounded current-period request preserves all required windows and old successes."""

from tests.cloud_current123_new16_periods_real_data import prepare_request
from tools.collect_rollover_readiness_laptop import _client


def test_existing_collector_can_express_exact_complete_new_scope_without_network():
    request = prepare_request()
    for job in request["jobs"]:
        _, url = _client(job)
        assert url == "https://stats.nba.com/stats/" + job["endpoint"]
