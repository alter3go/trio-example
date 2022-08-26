from functools import partial

import pytest
import trio
import trio.testing
from hypothesis import given
from hypothesis import strategies as st

from echoserver.echo import IdleTimeout, echo_handler


@pytest.fixture
def configured_handler(timeouts):
    return partial(echo_handler, idle_timeout=timeouts)


async def test_with_tcp_server(nursery, configured_handler):
    """The echo handler should work with a trio TCP server."""
    server = partial(trio.serve_tcp, configured_handler, port=0)
    listeners = await nursery.start(server)
    client_stream = await trio.testing.open_stream_to_socket_listener(listeners[0])

    await client_stream.send_all(b"What is up my world")

    assert await client_stream.receive_some() == b"What is up my world"


@given(
    st.floats(min_value=0, max_value=300),
    st.floats(min_value=0, max_value=300),
)
def test_times_out_if_no_input_on_connect(
    idle_timeout_seconds,
    idle_timeout_refresh_seconds,
):
    """The echo handler should time out after `idle_timeout_seconds` if no initial data is
    received."""
    clock = trio.testing.MockClock(autojump_threshold=0)

    async def task():
        with pytest.raises(trio.TooSlowError):
            async with trio.open_nursery() as nursery:
                nursery.start_soon(
                    echo_handler,
                    trio.testing.MemoryReceiveStream(),
                    IdleTimeout(
                        seconds=idle_timeout_seconds,
                        refresh_seconds=idle_timeout_refresh_seconds,
                    ),
                )
            assert trio.current_time() == idle_timeout_seconds

    trio.run(task, clock=clock)


@given(
    st.floats(min_value=1, max_value=300),
    st.floats(min_value=0, max_value=300),
)
def test_times_out_after_thirty_seconds_of_no_input(
    idle_timeout_seconds, idle_timeout_refresh_seconds
):
    """The echo handler should time out `idle_timeout_refresh_seconds` after last receiving
    data."""
    clock = trio.testing.MockClock(autojump_threshold=0)

    async def task():
        client_stream, server_stream = trio.testing.memory_stream_pair()

        with pytest.raises(trio.TooSlowError):
            async with trio.open_nursery() as nursery:
                await nursery.start(
                    echo_handler,
                    server_stream,
                    IdleTimeout(
                        seconds=idle_timeout_seconds,
                        refresh_seconds=idle_timeout_refresh_seconds,
                    ),
                )
                await trio.sleep(idle_timeout_seconds - 1)
                await client_stream.send_all(b"stay with me!")

        assert (
            trio.current_time()
            == idle_timeout_seconds - 1 + idle_timeout_refresh_seconds
        )

    trio.run(task, clock=clock)


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
