"""A trio example adapted and modified from the echo server from the tutorial at
https://trio.readthedocs.io/en/stable/tutorial.html."""
import os

import trio

from . import ServerConfig, server

config = ServerConfig(
    ECHO_PORT=os.getenv("ECHOSERVER_ECHO_PORT", 4000),
    HTTP_PORT=os.getenv("ECHOSERVER_HTTP_PORT", 4001),
    IDLE_TIMEOUT_REFRESH_SECONDS=float(
        os.getenv("ECHOSERVER_IDLE_TIMEOUT_SECONDS", 30)
    ),
    IDLE_TIMEOUT_SECONDS=float(os.getenv("ECHOSERVER_IDLE_TIMEOUT_SECONDS", 5)),
)
trio.run(server, config)
