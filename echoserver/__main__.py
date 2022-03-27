"""A trio example adapted and modified from the echo server from the tutorial at
https://trio.readthedocs.io/en/stable/tutorial.html."""
from itertools import count

import trio
from hypercorn.config import Config
from hypercorn.trio import serve as hypercorn_serve

from echoserver.echo import echo_handler
from echoserver.web import WEB_SERVER_SHUTDOWN_EVENT, app

ECHO_PORT = 4000
HTTPS_PORT = 4001

CONNECTION_ID_SEQUENCE = count()

config = Config()
config.bind = [f"localhost:{HTTPS_PORT}"]


async def wrapped_echo_handler(stream):
    """A wrapped echo handler that logs and catches errors"""
    ident = next(CONNECTION_ID_SEQUENCE)
    print(f"echo_server {ident}: started")
    try:
        await echo_handler(stream)
        print(f"echo_server {ident}: connection closed")
    except trio.TooSlowError:
        print(f"echo_server {ident}: closing idle connection")
    except Exception as exc:
        print(f"echo_server {ident}: crashed: {exc!r}")


async def main():
    async with trio.open_nursery() as nursery:
        # Start the echo server
        nursery.start_soon(trio.serve_tcp, wrapped_echo_handler, ECHO_PORT)
        # Start the web server
        await hypercorn_serve(
            app, config, shutdown_trigger=WEB_SERVER_SHUTDOWN_EVENT.wait
        )
        # Shut down echo server when web server finishes
        nursery.cancel_scope.cancel()


trio.run(main)
