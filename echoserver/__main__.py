"""A trio example adapted and modified from the echo server from the tutorial at
https://trio.readthedocs.io/en/stable/tutorial.html."""
import trio

from . import server

trio.run(server)
