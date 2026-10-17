"""Controlled fixture coverage, separate from the S3 actual-source gate."""

import pytest

from tests.test_subject_ownership_contract import _check_subjects


@pytest.mark.fixture_data
@pytest.mark.query
def test_s3_owned_scoring_and_venue_fixture(monkeypatch):
    _check_subjects("2025-26", monkeypatch)
