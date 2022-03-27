from functools import partial

import pytest
import trio
import trio.testing

from echoserver.echo import echo_handler


async def test_with_tcp_server(nursery):
    """The echo handler should work with a trio TCP server."""
    listeners = await nursery.start(partial(trio.serve_tcp, echo_handler, port=0))
    client_stream = await trio.testing.open_stream_to_socket_listener(listeners[0])

    await client_stream.send_all(b"What is up my world")

    assert await client_stream.receive_some() == b"What is up my world"


async def test_times_out_after_five_seconds_if_no_input_on_connect(autojump_clock):
    """The echo handler should time out in five seconds if no initial data is
    received."""
    with pytest.raises(trio.TooSlowError):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(echo_handler, trio.testing.MemoryReceiveStream())

    assert trio.current_time() == 5


async def test_times_out_after_thirty_seconds_of_no_input(autojump_clock):
    """The echo handler should time out thirty seconds after last receiving data."""
    client_stream, server_stream = trio.testing.memory_stream_pair()

    with pytest.raises(trio.TooSlowError):
        async with trio.open_nursery() as nursery:
            await nursery.start(echo_handler, server_stream)
            await trio.sleep(4)
            await client_stream.send_all(b"stay with me!")

    assert trio.current_time() == 34


async def test_with_lockstep_stream(nursery):
    """The echo handler should work with a completely unbuffered stream."""
    client_stream, server_stream = trio.testing.lockstep_stream_pair()
    received = b""

    nursery.start_soon(echo_handler, server_stream)
    await client_stream.send_all(b"Hello, ")
    while received != b"Hello, ":
        received += await client_stream.receive_some()
    await client_stream.send_all(b"world")
    while received != b"Hello, world":
        received += await client_stream.receive_some()

    assert received == b"Hello, world"
