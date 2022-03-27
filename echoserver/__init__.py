import logging
from dataclasses import dataclass
from typing import Optional

import hypercorn.config
import trio
from hypercorn.trio import serve as hypercorn_serve

from .echo import configure_echo_handler
from .web import configure_asgi_app

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    ECHO_PORT: int = 0
    HTTP_PORT: Optional[int] = None


async def server(config: ServerConfig, task_status=trio.TASK_STATUS_IGNORED):
    """A TCP server with listeners for echo and HTTP connections"""
    echo_handler = configure_echo_handler()
    asgi_app, shutdown_event = configure_asgi_app()

    hypercorn_config = hypercorn.config.Config()
    hypercorn_config.bind = (
        [f"localhost:{config.HTTP_PORT}"] if config.HTTP_PORT else ["localhost"]
    )

    async with trio.open_nursery() as nursery:
        # Start the echo server
        echo_listener: trio.SocketListener = (
            await nursery.start(trio.serve_tcp, echo_handler, config.ECHO_PORT)
        )[0]
        logger.info(
            f"Listening for echo traffic on {echo_listener.socket.getsockname()}"
        )
        # Signal that we've begun serving echo traffic
        task_status.started(echo_listener)
        # Start the web server
        await hypercorn_serve(
            asgi_app, hypercorn_config, shutdown_trigger=shutdown_event.wait
        )
        # Shut down echo server when web server finishes
        nursery.cancel_scope.cancel()
