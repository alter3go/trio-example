from functools import partial
from itertools import count

import hypercorn.trio as hypercorn_trio
import trio
from hypercorn.config import Config
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route

ECHO_PORT = 4000
ECHO_INITIAL_IDLE_TIMEOUT = 5
ECHO_REFRESH_IDLE_TIMEOUT = 30
HTTPS_PORT = 4001

CONNECTION_ID_SEQUENCE = count()

WEB_SERVER_SHUTDOWN_EVENT = trio.Event()


async def healthcheck(_: Request) -> Response:
    """A simple healthcheck HTTP endpoint"""
    return PlainTextResponse("ok computer")


async def die(_: Request) -> Response:
    """An HTTP endpoint that tells the echo server to shut down"""
    print("Shutting down by request")
    WEB_SERVER_SHUTDOWN_EVENT.set()
    return PlainTextResponse("bye bye")


app = Starlette(
    debug=True,
    routes=[
        Route("/healthcheck", healthcheck),
        Route("/die", die, methods=["POST"]),
    ],
)
config = Config()
config.bind = [f"localhost:{HTTPS_PORT}"]


async def echo_handler(stream: trio.SocketStream):
    ident = next(CONNECTION_ID_SEQUENCE)
    print(f"echo_server {ident}: started")
    try:
        with trio.fail_after(
            ECHO_INITIAL_IDLE_TIMEOUT
        ) as timeout:  # only wait so long for initial data
            async for data in stream:
                timeout.deadline = (
                    trio.current_time() + ECHO_REFRESH_IDLE_TIMEOUT
                )  # extend deadline
                await stream.send_all(data)
        print(f"echo_server {ident}: connection closed")
    except trio.TooSlowError:
        print(f"echo_server {ident}: closing idle connection")
    except Exception as exc:
        print(f"echo_server {ident}: crashed: {exc!r}")


async def main():
    async with trio.open_nursery() as nursery:
        # Start the echo server
        serve_echo = partial(trio.serve_tcp)
        nursery.start_soon(serve_echo, echo_handler, ECHO_PORT)
        # Start the web server
        await hypercorn_trio.serve(
            app, config, shutdown_trigger=WEB_SERVER_SHUTDOWN_EVENT.wait
        )
        # Shut down echo server when web server finishes
        nursery.cancel_scope.cancel()


trio.run(main)
