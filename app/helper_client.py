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


async def docker_state(world: str = "main") -> str:
    resp = await _call("DOCKER_STATE", world=world)
    return resp.get("data", "")


async def logs_tail(world: str = "main") -> str:
    resp = await _call("LOGS_TAIL", timeout=30.0, world=world)
    return resp.get("data", "")


async def caretaking_status(world: str = "main") -> str:
    resp = await _call("CARETAKING_STATUS", world=world)
    return resp.get("data", "")


async def caretaking_force(world: str = "main") -> str:
    resp = await _call("CARETAKING_FORCE", world=world)
    return resp.get("data", "")


async def event_force(script: str, world: str = "main") -> str:
    resp = await _call("EVENT_FORCE", script=script, world=world)
    return resp.get("data", "")


async def event_allow_tonight(world: str = "main") -> str:
    resp = await _call("EVENT_ALLOW_TONIGHT", world=world)
    return resp.get("data", "")
