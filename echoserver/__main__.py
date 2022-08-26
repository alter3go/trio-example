"""A trio example adapted and modified from the echo server from the tutorial at
https://trio.readthedocs.io/en/stable/tutorial.html."""
import trio
from pydantic import BaseSettings

from . import ServerConfig, server


class Settings(BaseSettings):
    echoserver: ServerConfig = ServerConfig()

    class Config:
        env_nested_delimiter = "__"


config = Settings().echoserver
trio.run(server, config)
