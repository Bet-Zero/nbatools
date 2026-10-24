"""Cold identity decoration preserves ordered roster facts while overlapping I/O."""

import threading

from nbatools import query_service
from nbatools.data_source import (
    data_generation_context,
    data_source_cache_key,
    reset_data_source_cache,
)
from tests.test_data_source import FakeR2Client, _configure_r2, _generation_objects


def test_cold_identity_rosters_overlap_without_changing_precedence(monkeypatch, tmp_path):
    files = {
        f"raw/rosters/{year}.csv": (
            "player_id,player_name\n"
            f"{year},Roster Only\n203999,Nikola Jokić\ninvalid,Invalid Player\n"
        ).encode()
        for year in range(1996, 2026)
    }

    class OverlapClient(FakeR2Client):
        active = 0
        peak = 0
        lock = threading.Lock()
        paired = threading.Event()

        def get_object(self, *, Bucket, Key):
            if "/rosters/" not in Key:
                return super().get_object(Bucket=Bucket, Key=Key)
            with self.lock:
                self.active += 1
                self.peak = max(self.peak, self.active)
                if self.active > 1:
                    self.paired.set()
            try:
                self.paired.wait(timeout=0.05)
                return super().get_object(Bucket=Bucket, Key=Key)
            finally:
                with self.lock:
                    self.active -= 1

    client = OverlapClient(_generation_objects("identity-a", files))
    _configure_r2(monkeypatch, tmp_path, client)
    query_service._player_identity_lookup.cache_clear()
    try:
        with data_generation_context():
            # Moving the pointer cannot mix generations in worker threads.
            client.objects["metadata/active_generation.json"] = b'{"generation_id":"identity-b"}'
            key = data_source_cache_key()
            lookup = query_service._player_identity_lookup(key)
            assert lookup["roster only"] == {"player_id": 2025, "player_name": "Roster Only"}
            assert lookup["nikola jokic"]["player_id"] == 203999
            assert "invalid player" not in lookup
            calls = len(client.get_calls)
            assert query_service._player_identity_lookup(key) is lookup
            assert len(client.get_calls) == calls
        roster_calls = [k for k in client.get_calls if "/rosters/" in k]
        assert len(roster_calls) == len(set(roster_calls)) == 30
        assert all(k.startswith("generations/identity-a/") for k in roster_calls)
        assert 1 < client.peak <= 8
    finally:
        query_service._player_identity_lookup.cache_clear()
        reset_data_source_cache()
