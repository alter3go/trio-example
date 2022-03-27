import trio

ECHO_INITIAL_IDLE_TIMEOUT = 5
ECHO_REFRESH_IDLE_TIMEOUT = 30


async def echo_handler(stream: trio.SocketStream, task_status=trio.TASK_STATUS_IGNORED):
    with trio.fail_after(
        ECHO_INITIAL_IDLE_TIMEOUT
    ) as timeout:  # only wait so long for initial data
        task_status.started()
        async for data in stream:
            timeout.deadline = (
                trio.current_time() + ECHO_REFRESH_IDLE_TIMEOUT
            )  # extend deadline
            await stream.send_all(data)
