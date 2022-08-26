import pytest

from echoserver.echo import IdleTimeout


@pytest.fixture
def timeouts() -> IdleTimeout:
    return IdleTimeout(
        seconds=1,
        refresh_seconds=5,
    )
