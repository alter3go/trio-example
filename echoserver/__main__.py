"""A trio example adapted and modified from the echo server from the tutorial at
https://trio.readthedocs.io/en/stable/tutorial.html."""
import trio

from . import ServerConfig, server

config = ServerConfig(
    ECHO_PORT=4000,
    HTTP_PORT=4001,
)
trio.run(server, config)
