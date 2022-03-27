import logging
from typing import Tuple

import trio
from hypercorn.typing import ASGIFramework
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route

logger = logging.getLogger(__name__)


async def healthcheck(_: Request) -> Response:
    """A simple healthcheck HTTP endpoint"""
    return PlainTextResponse("ok computer")


async def die(request: Request) -> Response:
    """An HTTP endpoint that tells the echo server to shut down"""
    logger.info("Shutting down by request")
    request.app.state.shutdown_requested.set()
    return PlainTextResponse("bye bye")


def configure_asgi_app() -> Tuple[ASGIFramework, trio.Event]:
    app: ASGIFramework = Starlette(  # type: ignore
        debug=True,
        routes=[
            Route("/healthcheck", healthcheck),
            Route("/die", die, methods=["POST"]),
        ],
    )
    app.state.shutdown_requested = trio.Event()
    return app, app.state.shutdown_requested
