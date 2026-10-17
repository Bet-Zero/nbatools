import pytest

from tests.sample_order_contract import check_sample_order

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


@pytest.mark.parametrize("kind", ["team", "player"])
@pytest.mark.parametrize("operation", ["date", "window", "qualifying"])
def test_s5_actual_sample_order(kind, operation, monkeypatch):
    check_sample_order(kind, operation, monkeypatch)
