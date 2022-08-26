from typing import Optional

import hypercorn.config
import hypercorn.logging
import trio
from hypercorn.trio import serve as hypercorn_serve
from pydantic.dataclasses import dataclass

from .echo import IdleTimeout, configure_echo_handler
from .web import configure_asgi_app


@dataclass
class ServerConfig:
    echo_port: int = 4000
    http_port: Optional[int] = 4001
    log_level: Optional[str] = "INFO"
    idle_timeout: IdleTimeout = IdleTimeout()


async def server(config: ServerConfig, task_status=trio.TASK_STATUS_IGNORED):
    """A TCP server with listeners for echo and HTTP connections"""
    hypercorn_config = hypercorn.config.Config.from_mapping(
        {
            "bind": [f"localhost:{config.http_port}"]
            if config.http_port
            else ["localhost"],
            "loglevel": config.log_level,
        }
    )
    echo_handler = configure_echo_handler(config.idle_timeout, hypercorn_config.log)
    asgi_app, shutdown_event = configure_asgi_app()

    async with trio.open_nursery() as nursery:
        # Start the echo server
        echo_listener: trio.SocketListener = (
            await nursery.start(trio.serve_tcp, echo_handler, config.echo_port)
        )[0]
        sockname = echo_listener.socket.getsockname()
        echo_host, echo_port = sockname[0], sockname[1]
        await hypercorn_config.log.info(
            f"Listening for echo traffic on {echo_host}:{echo_port}"
        )
        # Signal that we've begun serving echo traffic
        task_status.started(echo_listener)
        # Start the web server
        await hypercorn_serve(
            asgi_app, hypercorn_config, shutdown_trigger=shutdown_event.wait
        )
        # Shut down echo server when web server finishes
        nursery.cancel_scope.cancel()
