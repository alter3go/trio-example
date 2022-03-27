Trio example
============
![Tests](https://github.com/alter3go/trio-example/actions/workflows/tests.yml/badge.svg)

This is a trivial TCP echo server that also runs an HTTP server for healthchecks and RPCs, adapted and expanded from the [Trio tutorial][trio-tutorial].

Microservices often need HTTP healthchecks even if their primary responsibility isn't to be an HTTP server. That's why implementing this service was a helpful way for me to get to know [Trio][trio-docs], the Python async framework for [structured concurrency][njs-blog], even if the end result isn't a very useful piece of software.

Another real world concern is testing. I was particularly delighted by what I was able to test in a Trio project. The code has 100% test coverage (aside from the trivial [`__main__.py`](./echoserver/__main__.py)), and tests several things which are typically hard to test properly:

- Idle timeouts and idle timeout refreshes
- Exit conditions for the server
- Streams being read/written in lockstep by the client (unbuffered client)

It does all this with only simulated sleeps on behalf of the client, so the tests run very quickly.

_None_ of the server code itself has any sleeps. The cancellation and scheduling points occur naturally in the design, and at no point is it necessary to wait an arbitrary amount of time to attempt to avoid a race.

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

```sh
$ python -m echoserver
```

Use netcat to connect to the echo server:

```sh
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

# Testing

To run the tests:

```sh
$ pytest
```

[trio-tutorial]: https://trio.readthedocs.io/en/stable/tutorial.html
[trio-docs]: https://trio.readthedocs.io/en/stable/index.html
[njs-blog]: https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful/
