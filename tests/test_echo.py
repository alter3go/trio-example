from functools import partial

import pytest
import trio
import trio.testing

from echoserver.echo import Timeouts, echo_handler


@pytest.fixture
def configured_handler(timeouts):
    return partial(echo_handler, timeouts=timeouts)


async def test_with_tcp_server(nursery, configured_handler):
    """The echo handler should work with a trio TCP server."""
    server = partial(trio.serve_tcp, configured_handler, port=0)
    listeners = await nursery.start(server)
    client_stream = await trio.testing.open_stream_to_socket_listener(listeners[0])

    await client_stream.send_all(b"What is up my world")

    assert await client_stream.receive_some() == b"What is up my world"


async def test_times_out_if_no_input_on_connect(autojump_clock):
    """The echo handler should time out in five seconds if no initial data is
    received."""
    with pytest.raises(trio.TooSlowError):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(
                echo_handler,
                trio.testing.MemoryReceiveStream(),
                Timeouts(
                    idle_timeout_seconds=5,
                    idle_timeout_refresh_seconds=30,
                ),
            )

    assert trio.current_time() == 5


async def test_times_out_after_thirty_seconds_of_no_input(autojump_clock):
    """The echo handler should time out thirty seconds after last receiving data."""
    client_stream, server_stream = trio.testing.memory_stream_pair()

    with pytest.raises(trio.TooSlowError):
        async with trio.open_nursery() as nursery:
            await nursery.start(
                echo_handler,
                server_stream,
                Timeouts(
                    idle_timeout_seconds=5,
                    idle_timeout_refresh_seconds=30,
                ),
            )
            await trio.sleep(4)
            await client_stream.send_all(b"stay with me!")

    assert trio.current_time() == 34


async def test_with_lockstep_stream(nursery, configured_handler):
    """The echo handler should work with a completely unbuffered stream."""
    client_stream, server_stream = trio.testing.lockstep_stream_pair()
    received = b""

    await nursery.start(configured_handler, server_stream)
    await client_stream.send_all(b"Hello, ")
    while received != b"Hello, ":
        received += await client_stream.receive_some()
    await client_stream.send_all(b"world")
    while received != b"Hello, world":
        received += await client_stream.receive_some()

    assert received == b"Hello, world"
