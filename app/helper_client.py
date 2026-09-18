import asyncio
import json
import os

HELPER_SOCK_ENV = "HELPER_SOCK"
DEFAULT_SOCK = "/run/pz-helper.sock"

_STREAM_LIMIT = 16 * 1024 * 1024


class HelperError(Exception):
    pass


async def _call(op: str, timeout: float = 15.0, **fields) -> dict:
    sock_path = os.environ.get(HELPER_SOCK_ENV, DEFAULT_SOCK)
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(sock_path, limit=_STREAM_LIMIT), timeout=timeout
        )
    except (OSError, asyncio.TimeoutError) as e:
        raise HelperError(f"cannot reach pz-helper at {sock_path}: {e}") from e

    try:
        request = {"op": op, **fields}
        writer.write((json.dumps(request) + "\n").encode("utf-8"))
        await writer.drain()

        try:
            line = await asyncio.wait_for(reader.readline(), timeout=timeout)
        except ValueError as e:
            raise HelperError(f"pz-helper response too large to read: {e}") from e
        if not line:
            raise HelperError("pz-helper closed the connection with no response")
        response = json.loads(line.decode("utf-8"))
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

    if not response.get("ok"):
        raise HelperError(response.get("error", "unknown helper error"))
    return response


async def docker_state() -> str:
    resp = await _call("DOCKER_STATE")
    return resp.get("data", "")


async def logs_tail() -> str:
    resp = await _call("LOGS_TAIL", timeout=30.0)
    return resp.get("data", "")


async def caretaking_status() -> str:
    resp = await _call("CARETAKING_STATUS")
    return resp.get("data", "")


async def caretaking_force() -> str:
    resp = await _call("CARETAKING_FORCE")
    return resp.get("data", "")


async def event_force(script: str) -> str:
    resp = await _call("EVENT_FORCE", script=script)
    return resp.get("data", "")


async def event_allow_tonight() -> str:
    resp = await _call("EVENT_ALLOW_TONIGHT")
    return resp.get("data", "")
