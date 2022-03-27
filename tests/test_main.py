from unittest import mock

import httpx
import pytest
import trio

from echoserver import ServerConfig
from echoserver import server as server_under_test
from echoserver.echo import Timeouts


@pytest.fixture
def server_config(timeouts: Timeouts) -> ServerConfig:
    return ServerConfig(
        IDLE_TIMEOUT_SECONDS=timeouts.idle_timeout_seconds,
        IDLE_TIMEOUT_REFRESH_SECONDS=timeouts.idle_timeout_refresh_seconds,
    )


@pytest.fixture
async def echo_port(nursery, server_config):
    """Starts a server and yields the port for the echo server"""
    listener = await nursery.start(server_under_test, server_config)
    yield listener.socket.getsockname()[1]  # yield the port


async def test_healthcheck(echo_port):
    """Make sure the healthcheck endpoint runs"""
    async with httpx.AsyncClient() as client:
        r: httpx.Response = await client.get("http://localhost:8000/healthcheck")
        assert r.status_code == 200
        assert r.text == "ok computer"


async def test_echo(echo_port):
    """Make sure the server serves echo connections"""
    stream = await trio.open_tcp_stream("localhost", echo_port)
    await stream.send_all(b"testing 123")
    assert await stream.receive_some() == b"testing 123"


async def test_server_dies_on_command(server_config):
    """The entire server dies when told to do so via HTTP endpoint"""
    async with trio.open_nursery() as nursery:
        await nursery.start(server_under_test, server_config)
        async with httpx.AsyncClient() as client:
            r: httpx.Response = await client.post("http://localhost:8000/die")
            assert r.status_code == 200
            assert r.text == "bye bye"
            # The test will hang here if the server is still running

    with pytest.raises(OSError):  # error stemming from connection refusal
        async with httpx.AsyncClient() as client:
            await client.get("http://localhost:8000/healthcheck")


async def test_wrapped_echo_server_handles_exceptions(autojump_clock, echo_port):
    """An exception in a handler does not kill the whole server"""
    with mock.patch(
        "echoserver.echo.echo_handler", side_effect=Exception
    ) as echo_handler:
        await trio.open_tcp_stream("localhost", echo_port)

    assert echo_handler.call_count == 1
    await trio.open_tcp_stream("localhost", echo_port)  # Still able to connect


async def test_wrapped_echo_server_runs_after_timeout(
    autojump_clock, echo_port, timeouts: Timeouts
):
    """An exception in a handler does not kill the whole server"""
    async with await trio.open_tcp_stream("localhost", echo_port):
        await trio.sleep(timeouts.idle_timeout_seconds * 10)  # sooo timed out!

    await trio.open_tcp_stream("localhost", echo_port)  # Still able to connect


async def test_wrapped_echo_server_runs_after_disconnect(autojump_clock, echo_port):
    """An client disconnection does not kill the whole server"""
    async with await trio.open_tcp_stream("localhost", echo_port):
        pass

    await trio.open_tcp_stream("localhost", echo_port)  # Still able to connect
