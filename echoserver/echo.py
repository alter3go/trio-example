import logging
from dataclasses import dataclass
from itertools import count
from typing import Optional

import trio

logger = logging.getLogger(__name__)


@dataclass
class EchoHandlerConfig:
    INITIAL_IDLE_TIMEOUT: float = 5
    REFRESH_IDLE_TIMEOUT: float = 30


async def echo_handler(
    stream: trio.SocketStream,
    config: Optional[EchoHandlerConfig] = None,
    task_status=trio.TASK_STATUS_IGNORED,
):
    """An echo server connection handler with idle timeouts."""
    config = config or EchoHandlerConfig()

    with trio.fail_after(
        config.INITIAL_IDLE_TIMEOUT
    ) as timeout:  # only wait so long for initial data
        task_status.started()
        async for data in stream:
            timeout.deadline = (
                trio.current_time() + config.REFRESH_IDLE_TIMEOUT
            )  # extend deadline
            await stream.send_all(data)


def configure_echo_handler(config: Optional[EchoHandlerConfig] = None):
    config = config or EchoHandlerConfig()
    CONNECTION_ID_SEQUENCE = count()

    async def wrapped_echo_handler(stream):
        """A wrapped echo handler that logs and catches errors."""
        ident = next(CONNECTION_ID_SEQUENCE)
        logger.info(f"echo_server {ident}: started")
        try:
            await echo_handler(stream, config)
            logger.info(f"echo_server {ident}: connection closed")
        except trio.TooSlowError:
            logger.warning(f"echo_server {ident}: closing idle connection")
        except Exception as exc:
            logger.error(f"echo_server {ident}: crashed: {exc!r}")

    return wrapped_echo_handler
