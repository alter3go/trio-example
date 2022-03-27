import pytest

from echoserver.echo import Timeouts


@pytest.fixture
def timeouts() -> Timeouts:
    return Timeouts(
        idle_timeout_seconds=1,
        idle_timeout_refresh_seconds=5,
    )
