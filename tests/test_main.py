from unittest import mock

import httpx
import trio

from echoserver import server


async def test_healthcheck(nursery):
    """Make sure the healthcheck endpoint runs"""
    await nursery.start(server)
    async with httpx.AsyncClient() as client:
        r: httpx.Response = await client.get("http://localhost:4001/healthcheck")
        assert r.status_code == 200
        assert r.text == "ok computer"


async def test_echo(nursery):
    """Make sure the server serves echo connections"""
    await nursery.start(server)
    stream = await trio.open_tcp_stream("localhost", 4000)
    await stream.send_all(b"testing 123")
    assert await stream.receive_some() == b"testing 123"


async def test_server_dies_on_command():
    """The entire server dies when told to do so via HTTP endpoint"""
    async with trio.open_nursery() as nursery:
        await nursery.start(server)
        async with httpx.AsyncClient() as client:
            r: httpx.Response = await client.post("http://localhost:4001/die")
            assert r.status_code == 200
            assert r.text == "bye bye"
    # The test will hang here if the server is still running, otherwise it will
    # fall off the end of the nursery


async def test_wrapped_echo_server_handles_exceptions(nursery, autojump_clock):
    """An exception in a handler does not kill the whole server"""
    await nursery.start(server)

    with mock.patch("echoserver.echo_handler", side_effect=Exception) as echo_handler:
        await trio.open_tcp_stream("localhost", 4000)

    assert echo_handler.call_count == 1
    await trio.open_tcp_stream("localhost", 4000)  # Still able to connect


async def test_wrapped_echo_server_runs_after_timeout(nursery, autojump_clock):
    """An exception in a handler does not kill the whole server"""
    await nursery.start(server)

    async with await trio.open_tcp_stream("localhost", 4000):
        await trio.sleep(5)

    await trio.open_tcp_stream("localhost", 4000)  # Still able to connect


async def test_wrapped_echo_server_runs_after_disconnect(nursery, autojump_clock):
    """An exception in a handler does not kill the whole server"""
    await nursery.start(server)

    async with await trio.open_tcp_stream("localhost", 4000):
        pass

    await trio.open_tcp_stream("localhost", 4000)  # Still able to connect
