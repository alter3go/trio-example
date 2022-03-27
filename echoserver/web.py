import trio
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route

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
