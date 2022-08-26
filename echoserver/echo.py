import logging
from dataclasses import dataclass
from itertools import count

import hypercorn.logging
import trio

logger = logging.getLogger(__name__)


@dataclass
class IdleTimeout:
    seconds: float = 5.0
    refresh_seconds: float = 30.0


async def echo_handler(
    stream: trio.SocketStream,
    idle_timeout: IdleTimeout,
    task_status=trio.TASK_STATUS_IGNORED,
):
    """An echo server connection handler with idle timeouts."""
    with trio.fail_after(
        idle_timeout.seconds
    ) as timeout:  # only wait so long for initial data
        task_status.started()
        async for data in stream:
            timeout.deadline = (
                trio.current_time() + idle_timeout.refresh_seconds
            )  # extend deadline
            await stream.send_all(data)


def configure_echo_handler(timeouts: IdleTimeout, logger: hypercorn.logging.Logger):
    CONNECTION_ID_SEQUENCE = count()

    async def wrapped_echo_handler(stream):
        """A wrapped echo handler that logs and catches errors."""
        ident = next(CONNECTION_ID_SEQUENCE)
        await logger.info(f"client {ident}: connected")
        try:
            await echo_handler(stream, timeouts)
            await logger.info(f"client {ident}: connection closed")
        except trio.TooSlowError:
            await logger.warning(f"client {ident}: closing idle connection")
        except Exception as exc:
            await logger.error(f"client {ident}: crashed: {exc!r}")

    return wrapped_echo_handler
