Trio example
============

# Setup

You'll need [poetry](https://python-poetry.org/) and Python 3.9 installed.
[Pyenv](https://github.com/pyenv/pyenv) is highly recommended for managing available
versions of Python on your system.

```sh
$ poetry shell
$ poetry install
$ pre-commit install
``` 

# Running

To run the echo server on port 4000, with an HTTP server on port 4001:

```
$ python -m echoserver
```

Use netcat to connect to the echo server:

```
$ nc localhost 4000
hey there
hey there
```

The HTTP server runs two endpoints: a healthcheck and an RPC endpoint that
terminates the server:

```
$ curl 'http://localhost:4001/healthcheck'
ok computer
$ curl -X POST 'http://localhost:4001/die'
bye bye
```

