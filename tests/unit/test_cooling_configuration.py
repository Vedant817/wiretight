from datetime import UTC, datetime, timedelta

import pytest

from app.core.oob import cooling_off_until


def test_configured_cooling_can_only_tighten():
    received = datetime(2026, 11, 14, tzinfo=UTC)
    called = received + timedelta(hours=2)
    assert cooling_off_until(
        callback_confirmed_at=called, change_request_received_at=received, cooling_off_hours=96
    ) == called + timedelta(hours=96)


@pytest.mark.parametrize("hours", [0, 1, 71, -1, True, 72.0])
def test_reduced_or_malformed_cooling_refused(hours):
    stamp = datetime(2026, 11, 14, tzinfo=UTC)
    with pytest.raises(ValueError, match="at least 72"):
        cooling_off_until(
            callback_confirmed_at=stamp, change_request_received_at=stamp, cooling_off_hours=hours
        )
