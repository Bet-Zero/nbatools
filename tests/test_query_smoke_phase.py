from __future__ import annotations

import pytest

from tests._query_smoke import (
    PHASE_QUERY_SMOKE_CASES,
    assert_api_query_smoke,
    assert_cli_query_smoke,
    case_id,
    run_api_query_smoke,
    run_cli_query_smoke,
)

pytestmark = pytest.mark.needs_data


@pytest.mark.parametrize("case", PHASE_QUERY_SMOKE_CASES, ids=case_id)
def test_cli_phase_query_smoke(case, tmp_path):
    stdout, payload = run_cli_query_smoke(case, tmp_path)
    assert_cli_query_smoke(case, stdout, payload)


@pytest.mark.parametrize("case", PHASE_QUERY_SMOKE_CASES, ids=case_id)
def test_api_phase_query_smoke(case):
    body = run_api_query_smoke(case)
    assert_api_query_smoke(case, body)
