from unittest import mock

import httpx
import pytest
import trio

from echoserver import ServerConfig
from echoserver import server as server_under_test


@pytest.fixture
async def echo_port(nursery):
    """Starts a server and yields the port for the echo server"""
    listener = await nursery.start(server_under_test, ServerConfig())
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


async def test_server_dies_on_command():
    """The entire server dies when told to do so via HTTP endpoint"""
    async with trio.open_nursery() as nursery:
        await nursery.start(server_under_test, ServerConfig())
        async with httpx.AsyncClient() as client:
            r: httpx.Response = await client.post("http://localhost:8000/die")
            assert r.status_code == 200
            assert r.text == "bye bye"
    # The test will hang here if the server is still running, otherwise it will
    # fall off the end of the nursery


async def test_wrapped_echo_server_handles_exceptions(autojump_clock, echo_port):
    """An exception in a handler does not kill the whole server"""
    with mock.patch(
        "echoserver.echo.echo_handler", side_effect=Exception
    ) as echo_handler:
        await trio.open_tcp_stream("localhost", echo_port)

    assert echo_handler.call_count == 1
    await trio.open_tcp_stream("localhost", echo_port)  # Still able to connect


async def test_wrapped_echo_server_runs_after_timeout(autojump_clock, echo_port):
    """An exception in a handler does not kill the whole server"""
    async with await trio.open_tcp_stream("localhost", echo_port):
        await trio.sleep(5)

    await trio.open_tcp_stream("localhost", echo_port)  # Still able to connect


async def test_wrapped_echo_server_runs_after_disconnect(autojump_clock, echo_port):
    """An exception in a handler does not kill the whole server"""
    async with await trio.open_tcp_stream("localhost", echo_port):
        pass

    await trio.open_tcp_stream("localhost", echo_port)  # Still able to connect
