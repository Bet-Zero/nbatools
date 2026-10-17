import pytest

from tests.sample_order_contract import check_sample_order

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


@pytest.mark.parametrize("kind", ["team", "player"])
@pytest.mark.parametrize("operation", ["date", "window", "qualifying"])
def test_s5_controlled_sample_order(kind, operation, monkeypatch):
    check_sample_order(kind, operation, monkeypatch)


@pytest.mark.parametrize(
    "outcome,unit",
    [({}, "games"), ({"wins_only": True}, "wins"), ({"losses_only": True}, "losses")],
)
def test_outcome_window_label_keeps_effective_outcome(outcome, unit):
    from nbatools.query_service import _build_applied_filters

    labels = _build_applied_filters(
        {"last_n": 3, "last_n_scope": "outcome_window"}, route_kwargs=outcome
    )
    assert {
        "label": "Sample selection",
        "kind": "window",
        "value": f"Check conditions within the last 3 {unit}",
    } in labels


def test_structured_last_n_default_is_labeled_qualifying():
    from nbatools.query_service import execute_structured_query

    result = execute_structured_query(
        "team_record", team="BOS", season="2023-24", last_n=3, stat="pts", min_value=110
    )
    assert result.result_status == "ok"
    assert result.metadata["last_n_scope"] == "qualifying"
    assert {
        "label": "Sample selection",
        "kind": "window",
        "value": "Select the last 3 games matching the conditions",
    } in result.metadata["applied_filters"]
