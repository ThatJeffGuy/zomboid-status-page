#!/usr/bin/env python3
import asyncio
import json
import logging
import os
import re
import stat
import subprocess

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s pz-helper: %(message)s")
log = logging.getLogger("pz-helper")

SOCK_PATH = os.environ.get("PZ_HELPER_SOCK", "/run/pz-helper/helper.sock")
CONTAINER = os.environ.get("PZ_GAME_CONTAINER", "zomboid-server")
CARETAKING_SCRIPT = os.environ.get("PZ_CARETAKING_SCRIPT", "/opt/app/zomboid/config/storms/caretaking.sh")
EVENTS_SCRIPT = os.environ.get("PZ_EVENTS_SCRIPT", "/opt/app/zomboid/config/storms/storms.sh")
LOG_SINCE = "1h"

_EVENT_SCRIPT_RE = re.compile(r"^storm-[a-z0-9]+\.sh$")


def _docker_state() -> str:
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}} {{.State.StartedAt}}", CONTAINER],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "docker inspect failed")
    return result.stdout.strip()


LOG_TAIL_LINES = 20000


def _logs_tail() -> str:
    result = subprocess.run(
        ["docker", "logs", "--since", LOG_SINCE, "--tail", str(LOG_TAIL_LINES), CONTAINER],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "docker logs failed")
    return result.stdout.strip()


def _caretaking(flag: str) -> str:
    subprocess.Popen(
        ["sudo", "-n", "-u", "root", CARETAKING_SCRIPT, flag],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return "started"


def _event_force(script: str) -> str:
    if not _EVENT_SCRIPT_RE.match(script):
        raise RuntimeError(f"refusing to force unrecognized storm script: {script!r}")
    subprocess.Popen(
        ["sudo", "-n", "-u", "root", EVENTS_SCRIPT, "--force", script],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return "started"


def _event_allow_tonight() -> str:
    result = subprocess.run(
        ["sudo", "-n", "-u", "root", EVENTS_SCRIPT, "--allow-tonight"],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "storms.sh --allow-tonight failed")
    return result.stdout.strip() or "waived"


OPS = {
    "DOCKER_STATE": lambda req: _docker_state(),
    "LOGS_TAIL": lambda req: _logs_tail(),
    "CARETAKING_STATUS": lambda req: _caretaking("--status"),
    "CARETAKING_FORCE": lambda req: _caretaking("--force"),
    "EVENT_FORCE": lambda req: _event_force(str(req.get("script", ""))),
    "EVENT_ALLOW_TONIGHT": lambda req: _event_allow_tonight(),
}


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    peer = writer.get_extra_info("peername")
    try:
        line = await asyncio.wait_for(reader.readline(), timeout=10)
        if not line:
            return
        req = json.loads(line.decode("utf-8"))
        op = req.get("op")
        handler = OPS.get(op)
        if handler is None:
            response = {"ok": False, "error": f"unknown op: {op!r}"}
        else:
            try:
                data = await asyncio.to_thread(handler, req)
                response = {"ok": True, "data": data}
            except Exception as e:
                log.warning("op %s failed: %s", op, e)
                response = {"ok": False, "error": str(e)}
    except (asyncio.TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as e:
        response = {"ok": False, "error": f"bad request: {e}"}
    except Exception as e:
        log.exception("unexpected error handling client %s", peer)
        response = {"ok": False, "error": "internal error"}

    try:
        writer.write((json.dumps(response) + "\n").encode("utf-8"))
        await writer.drain()
    finally:
        writer.close()


async def main() -> None:
    sock_dir = os.path.dirname(SOCK_PATH)
    os.makedirs(sock_dir, exist_ok=True)
    if os.path.exists(SOCK_PATH):
        os.remove(SOCK_PATH)

    server = await asyncio.start_unix_server(handle_client, path=SOCK_PATH)

    os.chmod(SOCK_PATH, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)

    log.info("listening on %s", SOCK_PATH)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
