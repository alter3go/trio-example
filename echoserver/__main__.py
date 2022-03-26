from anyio import TASK_STATUS_IGNORED
import trio
from hypercorn.config import Config
import hypercorn.trio as hypercorn_trio
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from itertools import count
from functools import partial


ECHO_PORT = 4000
HTTPS_PORT = 4001

CONNECTION_COUNTER = count()

SHUTDOWN_EVENT = trio.Event()


async def healthcheck(_):
    return PlainTextResponse("ok computer")


async def die(_):
    SHUTDOWN_EVENT.set()
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


async def echo_handler(server_stream):
    ident = next(CONNECTION_COUNTER)
    print(f"echo_server {ident}: started")
    try:
        with trio.fail_after(10) as timeout:  # only wait 10 seconds to receive data
            async for data in server_stream:
                timeout.deadline += 60  # extend deadline a minute
                print(f"echo_server {ident}: received data {data!r}")
                await server_stream.send_all(data)
        print(f"echo_server {ident}: connection closed")
    except trio.TooSlowError:
        print(f"echo_server {ident}: closing idle connection")
    except Exception as exc:
        print(f"echo_server {ident}: crashed: {exc!r}")


async def main():
    async with trio.open_nursery() as nursery:
        async with trio.open_nursery() as echo_nursery:
            # Start the web server
            serve_web = partial(hypercorn_trio.serve, shutdown_trigger=SHUTDOWN_EVENT.wait)
            nursery.start_soon(serve_web, app, config)
            # Start the echo server
            serve_echo = partial(trio.serve_tcp, handler_nursery=echo_nursery)
            echo_nursery.start_soon(serve_echo, echo_handler, ECHO_PORT)
            # Wait for shutdown event coming from the webserver,
            # then shutdown the echo server
            await SHUTDOWN_EVENT.wait()
            print("Received shutdown from webserver. Quitting")
            echo_nursery.cancel_scope.cancel()
        

trio.run(main)
