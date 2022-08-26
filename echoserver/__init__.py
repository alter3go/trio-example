import logging
from typing import Optional

import hypercorn.config
import trio
from hypercorn.trio import serve as hypercorn_serve
from pydantic.dataclasses import dataclass

from .echo import IdleTimeout, configure_echo_handler
from .web import configure_asgi_app

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    echo_port: int = 4000
    http_port: Optional[int] = 4001
    idle_timeout: IdleTimeout = IdleTimeout()


async def server(config: ServerConfig, task_status=trio.TASK_STATUS_IGNORED):
    """A TCP server with listeners for echo and HTTP connections"""
    echo_handler = configure_echo_handler(config.idle_timeout)
    asgi_app, shutdown_event = configure_asgi_app()

    hypercorn_config = hypercorn.config.Config()
    hypercorn_config.bind = (
        [f"localhost:{config.http_port}"] if config.http_port else ["localhost"]
    )

    async with trio.open_nursery() as nursery:
        # Start the echo server
        echo_listener: trio.SocketListener = (
            await nursery.start(trio.serve_tcp, echo_handler, config.echo_port)
        )[0]
        echo_port = echo_listener.socket.getsockname()[0]
        logger.info(f"Listening for echo traffic on localhost:{echo_port}")
        # Signal that we've begun serving echo traffic
        task_status.started(echo_listener)
        # Start the web server
        await hypercorn_serve(
            asgi_app, hypercorn_config, shutdown_trigger=shutdown_event.wait
        )
        # Shut down echo server when web server finishes
        nursery.cancel_scope.cancel()
